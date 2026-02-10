import uuid
import secrets
import os
import traceback
import logging
import asyncio
import time
from datetime import datetime
from typing import Literal

from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import (
    async_session_factory,
    Specialist,
    SpecialistAuthTelegram,
    SpecialistProfile,
    SpecialistStatus,
    TelegramBot,
    TelegramBotStatus,
    GoogleOAuthStatus,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    MessageLog, 
    LogDirection,
    BotHealthCheck,
    BotHealthCheckStatus,
)
from services.crypto import encrypt_token, decrypt_token
# Используем локальный импорт внутри функций, если возникнут циклические зависимости,
# но здесь импортируем функцию логирования сообщений.
from logging_middleware import log_outbound_message
from services.google_oauth import get_auth_url
from services.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarInsufficientPermissionsError,
    create_and_cleanup_test_event,
    create_bot_calendar,
    list_calendars,
)
from services.onboarding import finalize_specialist_if_ready
from config import BACKEND_BASE_URL

router = Router()
logger = logging.getLogger(__name__)

# --- FSM States ---
class OnboardingStates(StatesGroup):
    waiting_for_public_name = State()
    waiting_for_bot_token = State()
    waiting_for_calendar_action = State()

# --- Constants ---
BASE_URL = BACKEND_BASE_URL

def _get_handle(user: types.User) -> str:
    """Helper to get user handle for logs"""
    if user.username:
        return f"@{user.username}"
    parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(parts) if parts else str(user.id)



def _calendar_action_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🆕 Создать отдельный календарь (рекомендовано)", callback_data="calendar:create")],
            [types.InlineKeyboardButton(text="📂 Выбрать существующий календарь", callback_data="calendar:select")],
        ]
    )


def _is_valid_public_name(public_name: str) -> bool:
    return 2 <= len(public_name) <= 80


def _pick_latest_active_bot(bots: list[TelegramBot]) -> TelegramBot | None:
    active_bots = [bot for bot in bots if bot.status == TelegramBotStatus.active]
    if not active_bots:
        return None
    return max(active_bots, key=lambda bot: (bot.updated_at or bot.created_at or datetime.min))


def _resolve_bot_registration_action(existing_bot: TelegramBot | None, specialist_id: uuid.UUID) -> Literal["create", "update", "blocked"]:
    if existing_bot is None:
        return "create"
    if existing_bot.specialist_id == specialist_id:
        return "update"
    return "blocked"


async def _set_webhook_with_retry(bot: Bot, webhook_url: str, retries: int = 2, timeout_sec: float = 5.0) -> None:
    for attempt in range(retries + 1):
        try:
            await bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
                request_timeout=timeout_sec,
            )
            return
        except TelegramRetryAfter as exc:
            if attempt >= retries:
                raise
            wait_time = min(getattr(exc, "retry_after", 1), 2)
            await asyncio.sleep(wait_time)
        except (TelegramNetworkError, TelegramServerError, asyncio.TimeoutError):
            if attempt >= retries:
                raise
async def _check_bot_status(
    token: str,
    timeout_sec: float = 3.0,
    retries: int = 1,
) -> tuple[str, types.User | None]:
    last_error = None
    for attempt in range(retries + 1):
        bot = Bot(token=token)
        try:
            me = await bot.get_me(request_timeout=timeout_sec)
            return "OK", me
        except TelegramUnauthorizedError:
            return "UNAUTHORIZED", None
        except (TelegramRetryAfter, TelegramNetworkError, TelegramServerError, asyncio.TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                continue
            return "TEMP_ERROR", None
        except TelegramAPIError as exc:
            last_error = exc
            if attempt < retries:
                continue
            return "TEMP_ERROR", None
        finally:
            await bot.session.close()

    raise RuntimeError(f"Unhandled status check error: {last_error}")

async def _log_error_to_db(bot: Bot, tg_user_id: int, error_text: str, handler_name: str):
    """
    Вспомогательная функция для прямой записи ошибки в БД внутри except блока.
    Это гарантирует, что traceback сохранится, даже если мы не пробрасываем исключение выше.
    """
    try:
        async with async_session_factory() as session:
            # Пытаемся определить bot_id, если возможно
            bot_id = bot.id if bot else 0
            
            log_entry = MessageLog(
                bot_id=bot_id,
                tg_user_id=tg_user_id,
                direction=LogDirection.OUT, # Считаем это системным ответом/ошибкой
                message_type="error",
                content="Internal Server Error",
                is_error=True,
                error_details=error_text,
                handler_name=handler_name,
                created_at=datetime.utcnow()
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to log error to DB: {e}")

async def _log_bot_health_check(
    specialist_id: uuid.UUID,
    bot_user_id: int,
    status: BotHealthCheckStatus,
    latency_ms: int,
    error_details: str | None = None,
) -> None:
    try:
        async with async_session_factory() as session:
            entry = BotHealthCheck(
                specialist_id=specialist_id,
                bot_user_id=bot_user_id,
                status=status,
                latency_ms=latency_ms,
                error_details=error_details,
            )
            session.add(entry)
            await session.commit()
        logger.info(
            "Bot health check saved: specialist_id=%s bot_id=%s status=%s latency_ms=%s",
            specialist_id,
            bot_user_id,
            status.value,
            latency_ms,
        )
    except Exception as exc:
        logger.warning(
            "Failed to save bot health check: specialist_id=%s bot_id=%s status=%s error=%s",
            specialist_id,
            bot_user_id,
            status.value,
            exc.__class__.__name__,
            exc_info=True,
        )

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)

    try:
        async with async_session_factory() as session:
            auth_stmt = select(SpecialistAuthTelegram).where(
                SpecialistAuthTelegram.tg_user_id == tg_user_id
            )
            auth_res = await session.execute(auth_stmt)
            auth_entry = auth_res.scalar_one_or_none()

            if not auth_entry:
                text_out = "⚠️ Специалист не найден. Нажмите /start для регистрации."
                await message.answer(text_out)
                await log_outbound_message(
                    message.bot,
                    tg_user_id,
                    text_out,
                    user_handle=user_handle,
                )
                return

            bot_stmt = (
                select(TelegramBot)
                .where(
                    TelegramBot.specialist_id == auth_entry.specialist_id,
                    TelegramBot.status == TelegramBotStatus.active,
                )
                .order_by(TelegramBot.created_at.desc())
            )
            bot_res = await session.execute(bot_stmt)
            tg_bot = bot_res.scalars().first()

        if not tg_bot:
            text_out = "❌ Бот не подключен. Обновите токен через /start."
            await message.answer(text_out)
            await log_outbound_message(
                message.bot,
                tg_user_id,
                text_out,
                user_handle=user_handle,
            )
            return

        logger.info(
            "Status check requested: specialist_id=%s bot_id=%s",
            auth_entry.specialist_id,
            tg_bot.bot_user_id,
        )

        decrypted_token = decrypt_token(tg_bot.bot_token_encrypted)
        start_time = time.monotonic()
        status, bot_info = await _check_bot_status(decrypted_token, timeout_sec=3.0, retries=1)
        latency_ms = int((time.monotonic() - start_time) * 1000)
        db_status = {
            "OK": BotHealthCheckStatus.ok,
            "UNAUTHORIZED": BotHealthCheckStatus.unauthorized,
            "TEMP_ERROR": BotHealthCheckStatus.temp_error,
        }.get(status, BotHealthCheckStatus.temp_error)
        await _log_bot_health_check(
            auth_entry.specialist_id,
            tg_bot.bot_user_id,
            db_status,
            latency_ms,
        )

        logger.info(
            "Status check result: specialist_id=%s bot_id=%s status=%s latency_ms=%s",
            auth_entry.specialist_id,
            tg_bot.bot_user_id,
            status,
            latency_ms,
        )

        if status == "OK" and bot_info:
            text_out = f"✅ Бот доступен: @{bot_info.username} (id={bot_info.id})"
        elif status == "UNAUTHORIZED":
            text_out = "❌ Токен бота недействителен или бот удалён. Обновите токен через /start"
        else:
            text_out = "⚠️ Временно не удалось проверить бота. Повторите позже."

        await message.answer(text_out)
        await log_outbound_message(
            message.bot,
            tg_user_id,
            text_out,
            user_handle=user_handle,
        )

    except Exception:
        error_trace = traceback.format_exc()
        logger.error(f"Critical error in cmd_status: {error_trace}")
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "cmd_status")
        await message.answer("⚠️ Произошла внутренняя ошибка при проверке бота.")

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Умный старт: проверяет текущий статус специалиста и показывает чек-лист.
    Восстанавливает контекст FSM в зависимости от того, чего не хватает.
    """
    tg_user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    user_handle = _get_handle(message.from_user)
    
    try:
        async with async_session_factory() as session:
            # 1. Поиск по авторизации Telegram
            stmt = select(SpecialistAuthTelegram).where(
                SpecialistAuthTelegram.tg_user_id == tg_user_id
            )
            result = await session.execute(stmt)
            auth_entry = result.scalar_one_or_none()

            # --- СЦЕНАРИЙ 1: Новый пользователь ---
            if not auth_entry:
                new_specialist = Specialist(status=SpecialistStatus.onboarding)
                session.add(new_specialist)
                await session.flush()

                new_auth = SpecialistAuthTelegram(
                    specialist_id=new_specialist.specialist_id,
                    tg_user_id=tg_user_id,
                    tg_username=username,
                    tg_first_name=first_name,
                    tg_last_name=last_name
                )
                session.add(new_auth)
                await session.commit()
                
                text_out = (
                    "👋 **Добро пожаловать в платформу записи клиентов!**\n\n"
                    "Я помогу вам создать личного бота и подключить Google Календарь.\n"
                    "Нажмите кнопку ниже, чтобы начать настройку."
                )
                await message.answer(
                    text_out,
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[[types.KeyboardButton(text="🚀 Стать специалистом")]],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
                )
                await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=None, user_handle=user_handle)
                return

            # --- СЦЕНАРИЙ 2: Пользователь уже есть, проверяем прогресс ---
            
            # Загружаем специалиста со всеми связями
            # ВАЖНО: telegram_bots - это список!
            spec_stmt = (
                select(Specialist)
                .options(
                    selectinload(Specialist.profile),
                    selectinload(Specialist.telegram_bots),
                    selectinload(Specialist.google_oauth),
                    selectinload(Specialist.calendar_settings)
                )
                .where(Specialist.specialist_id == auth_entry.specialist_id)
            )
            spec_result = await session.execute(spec_stmt)
            specialist = spec_result.scalar_one()

            # Анализируем данные (Attribute Safety Check)
            has_profile = specialist.profile is not None
            
            # Проверяем список telegram_bots (не .bot, не .telegram_bot!)
            # Ищем предсказуемо: активный бот с самым свежим updated_at/created_at
            active_bot = _pick_latest_active_bot(specialist.telegram_bots or [])

            has_bot = active_bot is not None
            has_oauth = specialist.google_oauth is not None and specialist.google_oauth.status == GoogleOAuthStatus.connected
            has_calendar = specialist.calendar_settings is not None and bool(specialist.calendar_settings.calendar_id)
            smoke_ok = has_calendar and specialist.calendar_settings.last_smoke_test_status == "ok"

            if has_profile and has_bot and has_oauth and has_calendar and specialist.status == SpecialistStatus.onboarding:
                await finalize_specialist_if_ready(specialist.specialist_id)
                specialist.status = SpecialistStatus.active

            specialist_name = specialist.profile.public_name if has_profile else "Не задано"
            
            # Формируем чек-лист
            status_text = "📋 **Ваш статус настройки:**\n\n"
            
            if has_profile:
                status_text += f"✅ **Имя:** {specialist_name}\n"
            else:
                status_text += "❌ **Имя:** Не задано\n"
                
            if has_bot:
                status_text += f"✅ **Бот:** @{active_bot.bot_username}\n"
            else:
                status_text += "❌ **Бот:** Не подключен\n"
                
            if specialist.status == SpecialistStatus.active:
                status_text += "✅ **Статус:** Активен\n"
            else:
                status_text += "⏳ **Статус:** Онбординг\n"

            if has_oauth:
                status_text += "✅ **Google OAuth:** Подключен\n"
            else:
                status_text += "❌ **Google OAuth:** Не подключен\n"

            if has_calendar:
                status_text += f"✅ **Календарь бота:** {specialist.calendar_settings.calendar_summary or specialist.calendar_settings.calendar_id}\n"
                status_text += "✅ **Smoke-test:** Успешно\n" if smoke_ok else "❌ **Smoke-test:** Не пройден\n"
            else:
                status_text += "❌ **Календарь бота:** Не выбран\n"

            # Логика восстановления состояния (FSM)
            keyboard = None
            next_step_msg = ""
            new_state = None

            if not has_profile:
                await state.set_state(OnboardingStates.waiting_for_public_name)
                next_step_msg = "\n👇 **Действие:** Введите ваше публичное имя для клиентов."
                keyboard = types.ReplyKeyboardRemove()
                new_state = "waiting_for_public_name"
            
            elif not has_bot:
                await state.set_state(OnboardingStates.waiting_for_bot_token)
                next_step_msg = "\n👇 **Действие:** Пришлите токен вашего бота от @BotFather."
                keyboard = types.ReplyKeyboardRemove()
                new_state = "waiting_for_bot_token"

            elif not has_oauth:
                auth_url = get_auth_url(specialist.specialist_id)
                next_step_msg = "\n👇 **Действие:** Подключите Google аккаунт через кнопку ниже."
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(text="🔗 Подключить Google Календарь", url=auth_url)
                    ]]
                )
                await state.clear()
                new_state = "waiting_for_oauth"

            elif has_calendar:
                await state.set_state(OnboardingStates.waiting_for_calendar_action)
                next_step_msg = "\n✅ Календарь уже подключён. Можно перепроверить доступ."
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔁 Проверить доступ (smoke-test)", callback_data="calendar:smoke")],
                        [types.InlineKeyboardButton(text="♻️ Сменить календарь", callback_data="calendar:switch_stub")],
                    ]
                )
                new_state = "calendar_connected"

            else:
                await state.set_state(OnboardingStates.waiting_for_calendar_action)
                next_step_msg = "\n👇 **Действие:** Выберите как подключить рабочий календарь бота."
                keyboard = _calendar_action_keyboard()
                new_state = "waiting_for_calendar_action"
            
            final_text = status_text + next_step_msg
            await message.answer(final_text, reply_markup=keyboard)
            
            await log_outbound_message(
                message.bot, 
                tg_user_id, 
                final_text, 
                fsm_state=new_state, 
                user_handle=user_handle, 
                specialist_name=specialist_name if has_profile else None
            )

    except Exception:
        error_trace = traceback.format_exc()
        logger.error(f"Critical error in cmd_start: {error_trace}")
        
        # Логируем ошибку в БД
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "cmd_start")
        
        # Ответ пользователю
        await message.answer("⚠️ Произошла внутренняя ошибка при загрузке профиля. Администратор уведомлен.")


@router.message(F.text == "🚀 Стать специалистом")
async def start_flow(message: types.Message, state: FSMContext):
    await state.set_state(OnboardingStates.waiting_for_public_name)
    user_handle = _get_handle(message.from_user)
    
    text_out = (
        "📝 **Шаг 1 из 4. Публичное имя**\n\n"
        "Введите имя, которое будут видеть ваши клиенты.\n"
        "Например: *Психолог Анна* или *Иван Иванов*."
    )
    await message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
    await log_outbound_message(message.bot, message.from_user.id, text_out, fsm_state="waiting_for_public_name", user_handle=user_handle)


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    public_name = (message.text or "").strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)

    if not _is_valid_public_name(public_name):
        text_out = (
            "⚠️ Некорректное публичное имя. Используйте от 2 до 80 символов.\n"
            "Пример: *Психолог Анна* или *Иван Иванов*."
        )
        await message.answer(text_out)
        await log_outbound_message(
            message.bot,
            tg_user_id,
            text_out,
            fsm_state="waiting_for_public_name",
            user_handle=user_handle,
        )
        await state.set_state(OnboardingStates.waiting_for_public_name)
        return

    try:
        async with async_session_factory() as session:
            stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            result = await session.execute(stmt)
            auth_entry = result.scalar_one()
            
            profile_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == auth_entry.specialist_id)
            profile_res = await session.execute(profile_stmt)
            profile = profile_res.scalar_one_or_none()

            if not profile:
                profile = SpecialistProfile(
                    specialist_id=auth_entry.specialist_id,
                    public_name=public_name,
                    owner_tg_user_id=tg_user_id,
                    owner_tg_username=message.from_user.username,
                    specialist_timezone="UTC",
                )
                session.add(profile)
            else:
                profile.public_name = public_name
                profile.owner_tg_user_id = tg_user_id
            await session.commit()

        await state.set_state(OnboardingStates.waiting_for_bot_token)
        
        text_out = (
            f"✅ Имя сохранено: **{public_name}**\n\n"
            "🤖 **Шаг 2 из 4. Личный бот**\n\n"
            "1. Откройте @BotFather\n"
            "2. Создайте нового бота командой /newbot\n"
            "3. Скопируйте **API Token** и пришлите его сюда."
        )
        await message.answer(text_out)
        await log_outbound_message(
            message.bot, tg_user_id, text_out, 
            fsm_state="waiting_for_bot_token", user_handle=user_handle, specialist_name=public_name
        )

    except Exception:
        error_trace = traceback.format_exc()
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "process_public_name")
        await message.answer("⚠️ Ошибка сохранения имени. Попробуйте еще раз.")


@router.message(OnboardingStates.waiting_for_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    raw_token = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    
    specialist_id = None
    specialist_name = None

    try:
        # Получаем данные специалиста
        async with async_session_factory() as session:
            auth_stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            auth_res = await session.execute(auth_stmt)
            auth_entry = auth_res.scalar_one()
            specialist_id = auth_entry.specialist_id
            
            prof_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == specialist_id)
            prof_res = await session.execute(prof_stmt)
            prof = prof_res.scalar_one_or_none()
            if prof:
                specialist_name = prof.public_name

        # 1. Валидация токена
        temp_bot = Bot(token=raw_token)
        try:
            bot_info = await temp_bot.get_me(request_timeout=5.0)
        except Exception as e:
            text_out = f"❌ **Неверный токен**\nОшибка: `{e}`\nПроверьте токен и пришлите снова."
            await message.answer(text_out)
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
            return
        finally:
            await temp_bot.session.close()

        # 2. Подготовка данных Webhook и записи в БД
        webhook_secret = secrets.token_urlsafe(32)
        webhook_path = f"/tg/webhook/{bot_info.id}/{webhook_secret}"
        webhook_url = f"{BASE_URL}{webhook_path}"
        encrypted_token = encrypt_token(raw_token)

        async with async_session_factory() as session:
            check_bot = select(TelegramBot).where(TelegramBot.bot_user_id == bot_info.id)
            existing_bot = (await session.execute(check_bot)).scalar_one_or_none()
            action = _resolve_bot_registration_action(existing_bot, specialist_id)

            if action == "blocked":
                logger.warning(
                    "Bot registration blocked: bot_user_id=%s requested_by=%s owner=%s",
                    bot_info.id,
                    specialist_id,
                    existing_bot.specialist_id if existing_bot else None,
                )
                text_out = "⚠️ Этот бот уже зарегистрирован у другого специалиста."
                await message.answer(text_out)
                await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
                return

            if action == "update":
                existing_bot.bot_username = bot_info.username
                existing_bot.bot_name = bot_info.first_name
                existing_bot.bot_token_encrypted = encrypted_token
                existing_bot.webhook_secret = webhook_secret
                existing_bot.webhook_url = webhook_url
                existing_bot.status = TelegramBotStatus.active
                logger.info(
                    "Bot token updated for existing specialist bot: specialist_id=%s bot_user_id=%s",
                    specialist_id,
                    bot_info.id,
                )
            else:
                new_bot = TelegramBot(
                    specialist_id=specialist_id,
                    bot_user_id=bot_info.id,
                    bot_username=bot_info.username,
                    bot_name=bot_info.first_name,
                    bot_token_encrypted=encrypted_token,
                    webhook_secret=webhook_secret,
                    webhook_url=webhook_url,
                    status=TelegramBotStatus.active,
                )
                session.add(new_bot)
                logger.info(
                    "New bot registered: specialist_id=%s bot_user_id=%s",
                    specialist_id,
                    bot_info.id,
                )

            await session.commit()

        # 3. Установка вебхука с retry
        temp_bot_webhook = Bot(token=raw_token)
        try:
            await _set_webhook_with_retry(temp_bot_webhook, webhook_url=webhook_url, retries=2, timeout_sec=5.0)
        except Exception as e:
            logger.warning(
                "Webhook setup failed after retries: specialist_id=%s bot_user_id=%s error=%s",
                specialist_id,
                bot_info.id,
                e.__class__.__name__,
            )
            text_out = "❌ Не удалось настроить webhook из-за временной ошибки Telegram. Попробуйте отправить токен ещё раз."
            await message.answer(text_out)
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
            await state.set_state(OnboardingStates.waiting_for_bot_token)
            return
        finally:
            await temp_bot_webhook.session.close()

        await finalize_specialist_if_ready(specialist_id)

        async with async_session_factory() as session:
            specialist_status = await session.get(Specialist, specialist_id)
            is_active_now = specialist_status is not None and specialist_status.status == SpecialistStatus.active

        # 4. Финиш
        await state.clear()
        
        auth_url = get_auth_url(specialist_id)

        status_line = "🟢 Статус специалиста: active." if is_active_now else "⏳ Статус специалиста: onboarding."
        text_out = (
            f"✅ Бот **@{bot_info.username}** успешно подключен!\n"
            f"{status_line}\n\n"
            f"📅 **Шаг 3 из 4:** Подключите Google аккаунт, затем выберите рабочий календарь бота."
        )
        
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(text="🔗 Подключить Google Календарь", url=auth_url)
            ]]
        )

        await message.answer(text_out, reply_markup=keyboard)
        await log_outbound_message(
            bot=message.bot,
            tg_user_id=tg_user_id,
            content=text_out + f" [Auth Link Generated]",
            fsm_state="waiting_for_oauth",
            user_handle=user_handle,
            specialist_name=specialist_name
        )

    except Exception:
        error_trace = traceback.format_exc()
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "process_bot_token")
        await message.answer("⚠️ Критическая ошибка при подключении бота.")


@router.callback_query(F.data == "calendar:select")
async def calendar_select_stub(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.waiting_for_calendar_action)
    text = (
        "ℹ️ Функция выбора существующего календаря будет добавлена в следующем релизе.\n"
        "Сейчас используйте ‘Создать отдельный календарь’."
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "calendar:switch_stub")
async def calendar_switch_stub(callback: types.CallbackQuery):
    await callback.message.answer("ℹ️ Смена календаря будет доступна в следующем релизе.")
    await callback.answer()


async def _upsert_calendar_settings(
    specialist_id: uuid.UUID,
    calendar_id: str,
    calendar_summary: str | None,
    calendar_tz: str | None,
    source: SpecialistCalendarSource,
    smoke_status: str | None = None,
    smoke_error: str | None = None,
):
    async with async_session_factory() as session:
        stmt = select(SpecialistCalendarSettings).where(SpecialistCalendarSettings.specialist_id == specialist_id)
        settings = (await session.execute(stmt)).scalar_one_or_none()
        now = datetime.utcnow()

        if not settings:
            settings = SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                calendar_summary=calendar_summary,
                calendar_time_zone=calendar_tz,
                source=source,
            )
            session.add(settings)
        else:
            settings.calendar_id = calendar_id
            settings.calendar_summary = calendar_summary
            settings.calendar_time_zone = calendar_tz
            settings.source = source

        if smoke_status is not None:
            settings.last_smoke_test_status = smoke_status
            settings.last_smoke_test_at = now
            settings.last_smoke_test_error = smoke_error

        await session.commit()


async def _notify_personal_bot_welcome(specialist_id: uuid.UUID, tg_user_id: int) -> str | None:
    async with async_session_factory() as session:
        stmt = select(TelegramBot).where(
            TelegramBot.specialist_id == specialist_id,
            TelegramBot.status == TelegramBotStatus.active,
        )
        personal_bot = (await session.execute(stmt)).scalar_one_or_none()

    if not personal_bot:
        return None

    bot_token = decrypt_token(personal_bot.bot_token_encrypted)
    personal = Bot(token=bot_token)
    try:
        await personal.send_message(chat_id=tg_user_id, text="🎉 Личный бот готов к работе.")
    except Exception:
        logger.warning("Failed to send welcome message to personal bot", exc_info=True)
    finally:
        await personal.session.close()

    return personal_bot.bot_username


@router.callback_query(F.data == "calendar:create")
async def calendar_create(callback: types.CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    try:
        async with async_session_factory() as session:
            auth = (await session.execute(select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id))).scalar_one_or_none()
            if not auth:
                await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
                await callback.answer()
                return

            specialist = (await session.execute(
                select(Specialist).options(selectinload(Specialist.profile), selectinload(Specialist.calendar_settings)).where(Specialist.specialist_id == auth.specialist_id)
            )).scalar_one()

        if specialist.calendar_settings and specialist.calendar_settings.calendar_id:
            await callback.message.answer("✅ Календарь уже подключён. Используйте /start для повторной проверки.")
            await callback.answer()
            return

        profile = specialist.profile
        if not profile:
            await callback.message.answer("⚠️ Сначала заполните профиль через /start.")
            await callback.answer()
            return

        calendar = await create_bot_calendar(specialist.specialist_id, profile.public_name, profile.specialist_timezone or "UTC")
        calendar_id = calendar.get("id")
        summary = calendar.get("summary")
        calendar_tz = calendar.get("timeZone") or profile.specialist_timezone or "UTC"

        await _upsert_calendar_settings(
            specialist.specialist_id,
            calendar_id=calendar_id,
            calendar_summary=summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.created,
        )

        try:
            await create_and_cleanup_test_event(specialist.specialist_id, calendar_id, calendar_tz)
            await _upsert_calendar_settings(
                specialist.specialist_id,
                calendar_id=calendar_id,
                calendar_summary=summary,
                calendar_tz=calendar_tz,
                source=SpecialistCalendarSource.created,
                smoke_status="ok",
            )
        except Exception as smoke_exc:
            await _upsert_calendar_settings(
                specialist.specialist_id,
                calendar_id=calendar_id,
                calendar_summary=summary,
                calendar_tz=calendar_tz,
                source=SpecialistCalendarSource.created,
                smoke_status="failed",
                smoke_error=str(smoke_exc)[:255],
            )
            await callback.message.answer(
                "❌ Календарь создан, но smoke-test не пройден: не удалось создать/удалить тестовое событие. "
                "Проверьте права Google и переподключите аккаунт."
            )
            await callback.answer()
            return

        await finalize_specialist_if_ready(specialist.specialist_id)
        personal_username = await _notify_personal_bot_welcome(specialist.specialist_id, tg_user_id)
        deep_link = f"https://t.me/{personal_username}" if personal_username else ""

        await state.clear()
        await callback.message.answer(
            "✅ Календарь подключён, всё готово. Теперь используйте вашего бота: "
            f"@{personal_username}\n{deep_link}"
        )
        await callback.answer()

    except GoogleCalendarInsufficientPermissionsError:
        await callback.message.answer(
            "⚠️ Google подключен, но доступов недостаточно для создания календаря/событий. "
            "Переподключите аккаунт через кнопку ‘Подключить Google Календарь’ в /start и выдайте все запрошенные права."
        )
        await callback.answer()
    except GoogleCalendarError as exc:
        logger.exception("Google calendar operation failed")
        await callback.message.answer(f"⚠️ Ошибка Google Calendar: {exc}")
        await callback.answer()
    except Exception:
        logger.exception("calendar_create failed")
        await callback.message.answer("⚠️ Не удалось подключить календарь. Попробуйте позже.")
        await callback.answer()


@router.callback_query(F.data == "calendar:smoke")
async def calendar_retest(callback: types.CallbackQuery):
    tg_user_id = callback.from_user.id
    try:
        async with async_session_factory() as session:
            auth = (await session.execute(select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id))).scalar_one_or_none()
            if not auth:
                await callback.message.answer("⚠️ Профиль специалиста не найден.")
                await callback.answer()
                return

            settings = (await session.execute(select(SpecialistCalendarSettings).where(SpecialistCalendarSettings.specialist_id == auth.specialist_id))).scalar_one_or_none()
            if not settings:
                await callback.message.answer("⚠️ Календарь ещё не подключен.")
                await callback.answer()
                return

            calendar_id = settings.calendar_id
            tz = settings.calendar_time_zone or "UTC"
            summary = settings.calendar_summary
            source = settings.source

        await create_and_cleanup_test_event(auth.specialist_id, calendar_id, tz)
        await _upsert_calendar_settings(auth.specialist_id, calendar_id, summary, tz, source, smoke_status="ok")
        await finalize_specialist_if_ready(auth.specialist_id)
        await callback.message.answer("✅ Smoke-test успешно выполнен.")
        await callback.answer()
    except Exception as exc:
        async with async_session_factory() as session:
            auth = (await session.execute(select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id))).scalar_one_or_none()
            settings = None
            if auth:
                settings = (await session.execute(select(SpecialistCalendarSettings).where(SpecialistCalendarSettings.specialist_id == auth.specialist_id))).scalar_one_or_none()
                if settings:
                    settings.last_smoke_test_status = "failed"
                    settings.last_smoke_test_at = datetime.utcnow()
                    settings.last_smoke_test_error = str(exc)[:255]
                    await session.commit()

        await callback.message.answer("❌ Smoke-test не пройден. Проверьте права Google и переподключите аккаунт.")
        await callback.answer()


@router.callback_query(F.data == "calendar:list_probe")
async def calendar_list_probe(callback: types.CallbackQuery):
    tg_user_id = callback.from_user.id
    async with async_session_factory() as session:
        auth = (await session.execute(select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id))).scalar_one_or_none()
    if not auth:
        await callback.answer()
        return
    try:
        items = await list_calendars(auth.specialist_id)
        await callback.message.answer(f"Доступно календарей: {len(items)}")
    except Exception:
        await callback.message.answer("Не удалось получить список календарей.")
    await callback.answer()
