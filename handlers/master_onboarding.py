import uuid
import secrets
import os
import traceback
import logging
import asyncio
import time
from datetime import datetime

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

router = Router()
logger = logging.getLogger(__name__)

# --- FSM States ---
class OnboardingStates(StatesGroup):
    waiting_for_public_name = State()
    waiting_for_bot_token = State()

# --- Constants ---
BASE_URL = os.getenv("BASE_URL", "https://api.example.com")

def _get_handle(user: types.User) -> str:
    """Helper to get user handle for logs"""
    if user.username:
        return f"@{user.username}"
    parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(parts) if parts else str(user.id)

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
                    selectinload(Specialist.google_oauth)
                )
                .where(Specialist.specialist_id == auth_entry.specialist_id)
            )
            spec_result = await session.execute(spec_stmt)
            specialist = spec_result.scalar_one()

            # Анализируем данные (Attribute Safety Check)
            has_profile = specialist.profile is not None
            
            # Проверяем список telegram_bots (не .bot, не .telegram_bot!)
            # Ищем хотя бы одного активного бота
            active_bot = None
            if specialist.telegram_bots:
                for b in specialist.telegram_bots:
                    if b.status == TelegramBotStatus.active:
                        active_bot = b
                        break
            
            has_bot = active_bot is not None
            has_oauth = specialist.google_oauth is not None and specialist.google_oauth.status == GoogleOAuthStatus.connected

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
                
            if has_oauth:
                status_text += "✅ **Google Calendar:** Подключен\n"
            else:
                status_text += "❌ **Google Calendar:** Не подключен\n"

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
                # Генерируем ссылку
                auth_url = get_auth_url(specialist.specialist_id)
                next_step_msg = "\n👇 **Действие:** Подключите календарь по кнопке ниже."
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(text="🔗 Подключить Google Календарь", url=auth_url)
                    ]]
                )
                # Состояние можно сбросить или оставить пустым
                await state.clear()
                new_state = "waiting_for_oauth"
            else:
                next_step_msg = "\n🎉 **Все настроено!** Можете переходить в свой бот и принимать клиентов."
                await state.clear()
                new_state = "completed"
            
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
        "📝 **Шаг 1 из 3. Публичное имя**\n\n"
        "Введите имя, которое будут видеть ваши клиенты.\n"
        "Например: *Психолог Анна* или *Иван Иванов*."
    )
    await message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
    await log_outbound_message(message.bot, message.from_user.id, text_out, fsm_state="waiting_for_public_name", user_handle=user_handle)


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    public_name = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)

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
            "🤖 **Шаг 2 из 3. Личный бот**\n\n"
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
            bot_info = await temp_bot.get_me()
        except Exception as e:
            text_out = f"❌ **Неверный токен**\nОшибка: `{e}`\nПроверьте токен и пришлите снова."
            await message.answer(text_out)
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
            return
        finally:
            await temp_bot.session.close()

        # 2. Установка вебхука
        webhook_secret = secrets.token_urlsafe(32)
        webhook_path = f"/tg/webhook/{bot_info.id}/{webhook_secret}"
        webhook_url = f"{BASE_URL}{webhook_path}"

        temp_bot_webhook = Bot(token=raw_token)
        try:
            await temp_bot_webhook.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
        except Exception as e:
            text_out = f"❌ **Ошибка настройки Webhook**\n`{e}`\nПопробуйте позже."
            await message.answer(text_out)
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
            await temp_bot_webhook.session.close()
            return
        finally:
            await temp_bot_webhook.session.close()

        # 3. Сохранение в БД
        encrypted_token = encrypt_token(raw_token)
        
        async with async_session_factory() as session:
            # Проверка дублей
            check_bot = select(TelegramBot).where(TelegramBot.bot_user_id == bot_info.id)
            existing_bot = (await session.execute(check_bot)).scalar_one_or_none()
            
            if existing_bot:
                text_out = "⚠️ Этот бот уже зарегистрирован в системе."
                await message.answer(text_out)
                await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state="waiting_for_bot_token", user_handle=user_handle)
                return

            new_bot = TelegramBot(
                specialist_id=specialist_id,
                bot_user_id=bot_info.id,
                bot_username=bot_info.username,
                bot_name=bot_info.first_name,
                bot_token_encrypted=encrypted_token,
                webhook_secret=webhook_secret,
                webhook_url=webhook_url,
                status=TelegramBotStatus.active
            )
            session.add(new_bot)
            await session.commit()

        # 4. Финиш
        await state.clear()
        
        auth_url = get_auth_url(specialist_id)

        text_out = (
            f"✅ Бот **@{bot_info.username}** успешно подключен!\n\n"
            f"📅 **Шаг 3 из 3. Google Календарь**\n\n"
            f"Подключите календарь, чтобы система знала ваше расписание."
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
