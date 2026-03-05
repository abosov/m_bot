import uuid
import secrets
import os
import traceback
import logging
import asyncio
import time
import re
from html import escape
from datetime import datetime, timezone
from typing import Literal

from aiogram import Router, F, types, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import (
    TelegramBadRequest,
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
    TariffPlan,
)
from services.crypto import encrypt_token, decrypt_token
# Используем локальный импорт внутри функций, если возникнут циклические зависимости,
# но здесь импортируем функцию логирования сообщений.
from logging_middleware import log_outbound_message
from services import web_connect
from services.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarInsufficientPermissionsError,
    create_and_cleanup_test_event,
    create_bot_calendar,
    ensure_calendar_watch,
    list_calendars,
    resolve_tz_for_calendar_creation,
)
from services.onboarding import finalize_specialist_if_ready
from services.specialist_defaults import apply_specialist_defaults_if_missing
from config import BACKEND_BASE_URL, PUBLIC_SITE_URL, MASTER_ONBOARDING_VIDEO_FILE_ID
from services.specialist_onboarding import get_specialist_by_tg_user_id, set_master_onboarding_completed
from services.specialists import ensure_specialist_with_profile_for_tg_user
from services.alerting import notify_exception
from services.referrals import attach_referrer_by_code, extract_referral_code
from services.log_context import log_event
from services.telegram.markdown_utils import escape_markdown_v2
from services.telegram.calendar_keyboard import build_calendar_selection_keyboard
from services.billing.subscriptions import create_subscription_purchase, get_latest_purchase_status_text

router = Router()
logger = logging.getLogger(__name__)

# --- FSM States ---
class OnboardingStates(StatesGroup):
    waiting_for_public_name = State()
    waiting_for_specialization = State()
    waiting_for_bot_token = State()
    waiting_for_calendar_action = State()

# --- Constants ---
BASE_URL = BACKEND_BASE_URL

_PLAN_PERIOD_LABELS = {
    "m": "месяц",
    "y": "год",
}

_PLAN_CARD_CONTENT = {
    TariffPlan.free: {
        "title": "Free",
        "description": "До 16 записей в месяц, напоминания клиентам и Google Calendar.",
        "price_m": "0 ₽",
        "price_y": "0 ₽",
    },
    TariffPlan.start: {
        "title": "Start",
        "description": "До 100 записей в месяц, напоминания и базовая статистика.",
        "price_m": "990 ₽ / мес",
        "price_y": "790 ₽ / мес (при оплате за год)",
    },
    TariffPlan.pro: {
        "title": "Pro",
        "description": "Безлимит записей, оплаты, интеграции и приоритетная поддержка.",
        "price_m": "2 490 ₽ / мес",
        "price_y": "1 990 ₽ / мес (при оплате за год)",
    },
    TariffPlan.team: {
        "title": "Team",
        "description": "Для команд и студий: роли, доступы и расширенная отчётность.",
        "price_m": "4 990 ₽ / мес",
        "price_y": "3 990 ₽ / мес (при оплате за год)",
    },
}


def _parse_plan_start_payload(raw_args: str | None) -> tuple[TariffPlan, str] | None:
    if not raw_args:
        return None
    payload = raw_args.strip().lower()
    if payload == "plan_team_contact":
        return TariffPlan.team, "m"
    if not payload.startswith("plan_"):
        return None

    parts = payload.split("_")
    if len(parts) != 3:
        return None

    _, plan_raw, period = parts
    if period not in _PLAN_PERIOD_LABELS:
        return None

    try:
        plan = TariffPlan(plan_raw)
    except ValueError:
        return None
    return plan, period


def _plan_choice_keyboard(plan: TariffPlan, period: str) -> types.InlineKeyboardMarkup:
    pricing_url = f"{PUBLIC_SITE_URL}/pricing"
    rows: list[list[types.InlineKeyboardButton]] = []
    if plan != TariffPlan.free:
        rows.append([types.InlineKeyboardButton(text="Перейти к оплате", callback_data=f"plan:pay_stub:{plan.value}:{period}")])
    rows.append([types.InlineKeyboardButton(text="Продолжить настройку", callback_data="onboarding:start")])
    rows.append([types.InlineKeyboardButton(text="Открыть тарифы на сайте", url=pricing_url)])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _build_plan_start_text(plan: TariffPlan, period: str) -> str:
    card = _PLAN_CARD_CONTENT[plan]
    period_label = _PLAN_PERIOD_LABELS[period]
    price = card["price_y"] if period == "y" else card["price_m"]
    return (
        f"✅ Вы выбрали тариф <b>{card['title']}</b> ({period_label}).\n\n"
        f"{card['description']}\n"
        f"Стоимость: <b>{price}</b>."
    )


async def _is_master_onboarding_completed(tg_user_id: int) -> bool:
    specialist = await get_specialist_by_tg_user_id(tg_user_id)
    return bool(specialist and specialist.onboarding_master_completed_at)


async def _handle_plan_start_payload(
    message: types.Message,
    state: FSMContext,
    command: CommandObject | None,
) -> bool:
    parsed = _parse_plan_start_payload(command.args if command else None)
    if not parsed:
        return False

    plan, period = parsed

    async with async_session_factory() as session:
        await ensure_specialist_with_profile_for_tg_user(
            session=session,
            tg_user_id=message.from_user.id,
            tg_username=message.from_user.username,
            tg_first_name=message.from_user.first_name,
            tg_last_name=message.from_user.last_name,
        )

    await state.clear()
    text_out = _build_plan_start_text(plan, period)
    await _send_safe_html_message(message, text_out, reply_markup=_plan_choice_keyboard(plan, period))
    await log_outbound_message(
        message.bot,
        message.from_user.id,
        text_out,
        fsm_state="plan_start",
        user_handle=_get_handle(message.from_user),
    )
    return True

def _get_handle(user: types.User) -> str:
    """Helper to get user handle for logs"""
    if user.username:
        return f"@{user.username}"
    parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(parts) if parts else str(user.id)


def _safe_username(username: str | None) -> str:
    if not username:
        return ""
    username = username.strip()
    if username.startswith("@"):
        username = username[1:]
    return username



def _build_personal_deep_link(bot_username: str | None) -> str:
    safe_username = _safe_username(bot_username)
    return f"https://t.me/{safe_username}?start=owner_panel" if safe_username else ""


def _build_connect_page_url(raw_token: str) -> str:
    return f"{PUBLIC_SITE_URL}/connect#token={raw_token}"


def _video_continue_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="Продолжить настройку", callback_data="video:continue")]]
    )


async def _send_onboarding_screen_for_state(
    callback: types.CallbackQuery,
    state: FSMContext,
    current_state: str | None,
) -> str | None:
    if current_state is None:
        return await _infer_and_send_onboarding_step(callback, state)

    if current_state == OnboardingStates.waiting_for_public_name.state:
        text_out = (
            "📝 **Шаг 1 из 5. Имя**\n\n"
            "Посмотреть видео-инструкцию: /video\n\n"
            "Введите имя, которое будут видеть ваши клиенты.\n"
            "Например: *Анна* или *Иван Иванов*."
        )
        await callback.message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
        return text_out

    if current_state == OnboardingStates.waiting_for_specialization.state:
        text_out = (
            "🧩 **Шаг 2 из 5. Специализация**\n\n"
            "Укажите вашу специализацию.\n"
            "Например: *Психолог*, *Коуч*, *Психотерапевт*, *Репетитор*."
        )
        await callback.message.answer(text_out)
        return text_out

    if current_state == OnboardingStates.waiting_for_bot_token.state:
        text_out = (
            "🤖 **Шаг 3 из 5. Личный бот**\n\n"
            "1. Откройте @BotFather\n"
            "2. Создайте нового бота командой /newbot\n"
            "3. Скопируйте **API Token** и пришлите его сюда."
        )
        await callback.message.answer(text_out)
        return text_out

    if current_state == OnboardingStates.waiting_for_calendar_action.state:
        await _calendar_select(callback, state)
        return None

    text_out = "Отправьте /start чтобы начать настройку."
    await callback.message.answer(text_out)
    return text_out


async def _infer_and_send_onboarding_step(
    callback: types.CallbackQuery,
    state: FSMContext,
) -> str | None:
    specialist = await get_specialist_by_tg_user_id(callback.from_user.id)
    if specialist is None:
        text_out = "Отправьте /start чтобы начать настройку."
        await callback.message.answer(text_out)
        return text_out

    async with async_session_factory() as session:
        spec_stmt = (
            select(Specialist)
            .options(
                selectinload(Specialist.profile),
                selectinload(Specialist.telegram_bots),
                selectinload(Specialist.google_oauth),
                selectinload(Specialist.calendar_settings),
            )
            .where(Specialist.specialist_id == specialist.specialist_id)
        )
        specialist = (await session.execute(spec_stmt)).scalar_one_or_none()

        if specialist is None:
            text_out = "Отправьте /start чтобы начать настройку."
            await callback.message.answer(text_out)
            return text_out

        has_profile = (
            specialist.profile is not None
            and bool((specialist.profile.public_name or "").strip())
        )
        has_specialization = bool((specialist.specialization or "").strip())
        has_bot = _pick_latest_active_bot(specialist.telegram_bots or []) is not None
        has_oauth = (
            specialist.google_oauth is not None
            and specialist.google_oauth.status == GoogleOAuthStatus.connected
        )
        has_calendar = (
            specialist.calendar_settings is not None
            and bool(specialist.calendar_settings.calendar_id)
        )

        if not has_profile:
            await state.set_state(OnboardingStates.waiting_for_public_name)
            text_out = (
                "📝 **Шаг 1 из 5. Имя**\n\n"
                "Посмотреть видео-инструкцию: /video\n\n"
                "Введите имя, которое будут видеть ваши клиенты.\n"
                "Например: *Анна* или *Иван Иванов*."
            )
            await callback.message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
            return text_out

        if not has_specialization:
            await state.set_state(OnboardingStates.waiting_for_specialization)
            text_out = (
                "🧩 **Шаг 2 из 5. Специализация**\n\n"
                "Укажите вашу специализацию.\n"
                "Например: *Психолог*, *Коуч*, *Психотерапевт*, *Репетитор*."
            )
            await callback.message.answer(text_out)
            return text_out

        if not has_bot:
            await state.set_state(OnboardingStates.waiting_for_bot_token)
            text_out = (
                "🤖 **Шаг 3 из 5. Личный бот**\n\n"
                "1. Откройте @BotFather\n"
                "2. Создайте нового бота командой /newbot\n"
                "3. Скопируйте **API Token** и пришлите его сюда."
            )
            await callback.message.answer(text_out)
            return text_out

        if not has_oauth:
            raw_token = await web_connect.create_connect_token(
                session,
                specialist.specialist_id,
                callback.from_user.id,
                ttl_minutes=15,
            )
            await session.commit()
            connect_url = _build_connect_page_url(raw_token)

            text_out = (
                "📅 <b>Шаг 4 из 5:</b> Подключите Google аккаунт.\n\n"
                "Откроется страница сайта. Подключение Google пройдет в браузере."
            )
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(text="Подключить Google Календарь", url=connect_url)
                ]]
            )
            await state.clear()
            await _send_safe_html_message(
                callback.message,
                text_out,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            return text_out

    if not has_calendar:
        await state.set_state(OnboardingStates.waiting_for_calendar_action)
        await _calendar_select(callback, state)
        return None

    text_out = "Настройка уже завершена. Используйте /start для статуса."
    await callback.message.answer(text_out)
    return text_out


def _full_onboarding_guard_keyboard(deep_link: str) -> types.InlineKeyboardMarkup:
    rows = []
    if deep_link:
        rows.append([types.InlineKeyboardButton(text="🚀 Перейти в персональный бот", url=deep_link)])
    rows.append([types.InlineKeyboardButton(text="🔁 Я уже завершил — проверить снова", callback_data="full_onboarding:recheck")])
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def _needs_personal_onboarding_prompt(specialist: Specialist) -> bool:
    return (
        specialist.onboarding_master_completed_at is not None
        and specialist.onboarding_personal_completed_at is None
    )


async def _send_safe_html_message(
    message: types.Message,
    text: str,
    *,
    reply_markup=None,
    disable_web_page_preview: bool | None = None,
) -> types.Message:
    kwargs = {"parse_mode": ParseMode.HTML, "reply_markup": reply_markup}
    if disable_web_page_preview is not None:
        kwargs["disable_web_page_preview"] = disable_web_page_preview
    try:
        return await message.answer(text, **kwargs)
    except TelegramBadRequest as exc:
        preview = text.replace("\n", " ")[:280]
        logger.warning("Telegram HTML parse failed in master_onboarding; fallback to plain text. preview=%r error=%s", preview, exc)
        return await message.answer(text, parse_mode=None, reply_markup=reply_markup)


async def _answer_plain(
    message: types.Message,
    text: str,
) -> types.Message:
    try:
        return await message.answer(text, parse_mode=None, disable_web_page_preview=True)
    except TelegramBadRequest as exc:
        if "can't parse entities" not in str(exc):
            raise
        logger.warning("Telegram plain-text fallback in master_onboarding; retry without preview flags")
        return await message.answer(text, parse_mode=None)




async def send_user_message(
    message: types.Message,
    text_out: str,
    *,
    reply_markup=None,
    fsm_state: str | None = None,
    specialist_name: str | None = None,
) -> types.Message:
    sent = await message.answer(text_out, reply_markup=reply_markup)
    await log_outbound_message(
        bot=message.bot,
        tg_user_id=message.from_user.id,
        content=text_out,
        fsm_state=fsm_state,
        specialist_name=specialist_name,
        user_handle=_get_handle(message.from_user),
    )
    return sent

async def _check_full_onboarding_or_prompt(message: types.Message, specialist: Specialist, personal_bot_username: str | None) -> bool:
    if not _needs_personal_onboarding_prompt(specialist):
        return True

    deep_link = _build_personal_deep_link(personal_bot_username)
    await _send_safe_html_message(
        message,
        "⏳ Онбординг ещё не завершён полностью. Перейдите в персональный бот, "
        "чтобы подтвердить/изменить стартовые настройки.\n"
        f"{deep_link if deep_link else 'Откройте вашего персонального бота по username.'}",
        reply_markup=_full_onboarding_guard_keyboard(deep_link),
    )
    return False


def _calendar_switch_keyboard(*, has_selected_calendar: bool) -> types.InlineKeyboardMarkup:
    button_text = "📅 Сменить календарь" if has_selected_calendar else "📅 Выбрать календарь"
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=button_text, callback_data="calendar:switch_stub")],
        ]
    )


def _normalize_calendar_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not item.get("id"):
            continue
        normalized.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "timeZone": item.get("timeZone"),
                "primary": bool(item.get("primary")),
                "accessRole": item.get("accessRole"),
            }
        )
    return normalized


def _calendar_select_keyboard(
    items: list[dict],
    page: int,
    per_page: int,
    current_calendar_id: str | None = None,
) -> types.InlineKeyboardMarkup:
    return build_calendar_selection_keyboard(
        items,
        page=page,
        per_page=per_page,
        current_calendar_id=current_calendar_id,
    )


def _calendar_select_text(total: int, page: int, per_page: int, has_readonly: bool) -> str:
    _ = (page, per_page, has_readonly)
    return (
        "📂 Шаг 5 из 5. Выбор календаря\n\n"
        "Выберите рабочий Google Календарь\n\n"
        f"Найдено календарей: {total}.\n"
        "Формат в списке: 📅 Название (Timezone).\nПосле выбора будет выполнена проверка интеграции."
    )


async def _render_calendar_selection(
    callback: types.CallbackQuery,
    state: FSMContext,
    items_norm: list[dict],
    page: int = 0,
    current_calendar_id: str | None = None,
) -> None:
    per_page = 6
    await state.update_data(
        cal_items=items_norm,
        cal_page=page,
        cal_per_page=per_page,
        cal_current_calendar_id=current_calendar_id,
    )
    await state.set_state(OnboardingStates.waiting_for_calendar_action)

    has_readonly = any(item.get("accessRole") == "reader" for item in items_norm)
    await callback.message.answer(
        _calendar_select_text(len(items_norm), page, per_page, has_readonly),
        reply_markup=_calendar_select_keyboard(items_norm, page, per_page, current_calendar_id),
    )


async def _start_calendar_select(callback: types.CallbackQuery, state: FSMContext) -> None:
    tg_user_id = callback.from_user.id
    async with async_session_factory() as session:
        auth = (
            await session.execute(
                select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()

    if not auth:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    items = await list_calendars(auth.specialist_id)
    items_norm = _normalize_calendar_items(items)

    async with async_session_factory() as session:
        settings = await session.get(SpecialistCalendarSettings, auth.specialist_id)
    current_calendar_id = settings.calendar_id if settings else None

    await _render_calendar_selection(callback, state, items_norm, page=0, current_calendar_id=current_calendar_id)
    await callback.answer()


def _is_valid_public_name(public_name: str) -> bool:
    return 2 <= len(public_name) <= 80


def _is_valid_specialization(specialization: str) -> bool:
    return bool(re.fullmatch(r"[0-9A-Za-zА-Яа-яЁё\s\-.]{2,120}", specialization))


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
                created_at=datetime.now(timezone.utc)
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

        specialist = await get_specialist_by_tg_user_id(tg_user_id)
        if specialist is None:
            await message.answer("⚠️ Профиль специалиста не найден. Нажмите /start для регистрации.")
            return
        await _check_full_onboarding_or_prompt(message, specialist, tg_bot.bot_username)

        onboarding_master = specialist.onboarding_master_completed_at.isoformat() if specialist.onboarding_master_completed_at else "—"
        onboarding_personal = specialist.onboarding_personal_completed_at.isoformat() if specialist.onboarding_personal_completed_at else "—"

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
            text_out = f"✅ Бот доступен: @{escape_markdown_v2(bot_info.username)} (id={bot_info.id})"
        elif status == "UNAUTHORIZED":
            text_out = "❌ Токен бота недействителен или бот удалён. Обновите токен через /start"
        else:
            text_out = "⚠️ Временно не удалось проверить бота. Повторите позже."

        text_out = (
            f"{text_out}\n"
            f"• Onboarding (master): {onboarding_master}\n"
            f"• Onboarding (personal): {onboarding_personal}"
        )
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
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject | None = None):
    """
    Умный старт: проверяет текущий статус специалиста и показывает чек-лист.
    Восстанавливает контекст FSM в зависимости от того, чего не хватает.
    """
    tg_user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    user_handle = _get_handle(message.from_user)

    if await _handle_plan_start_payload(message, state, command):
        return

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

                referral_code = extract_referral_code(command.args if command else None)
                await attach_referrer_by_code(session, new_specialist, referral_code)

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
                    "👋 <b>Добро пожаловать в платформу записи клиентов!</b>\n\n"
                    "Я помогу вам создать личного бота и подключить Google Календарь.\n"
                    "Нажмите кнопку ниже, чтобы начать настройку."
                )
                await _send_safe_html_message(
                    message,
                    text_out,
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[[types.KeyboardButton(text="🚀 Подключить сервис записи")]],
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
            has_profile = (
                specialist.profile is not None
                and bool((specialist.profile.public_name or "").strip())
            )
            
            # Проверяем список telegram_bots (не .bot, не .telegram_bot!)
            # Ищем предсказуемо: активный бот с самым свежим updated_at/created_at
            active_bot = _pick_latest_active_bot(specialist.telegram_bots or [])

            has_specialization = bool((specialist.specialization or "").strip())
            has_bot = active_bot is not None
            has_oauth = specialist.google_oauth is not None and specialist.google_oauth.status == GoogleOAuthStatus.connected
            has_calendar = specialist.calendar_settings is not None and bool(specialist.calendar_settings.calendar_id)
            smoke_ok = has_calendar and specialist.calendar_settings.last_smoke_test_status == "ok"

            if has_profile and has_bot and has_oauth and smoke_ok and specialist.status == SpecialistStatus.onboarding:
                await finalize_specialist_if_ready(specialist.specialist_id)

            specialist_name = specialist.profile.public_name if has_profile else "Не задано"
            
            # Формируем чек-лист
            status_text = "📋 <b>Ваш статус настройки:</b>\n\n"
            
            if has_profile:
                status_text += f"✅ <b>Имя:</b> {escape(specialist_name)}\n"
            else:
                status_text += "❌ <b>Имя:</b> Не задано\n"
                
            if has_bot:
                status_text += f"✅ <b>Бот:</b> @{escape(active_bot.bot_username or '')}\n"
            else:
                status_text += "❌ <b>Бот:</b> Не подключен\n"
                
            if specialist.status == SpecialistStatus.active:
                status_text += "✅ <b>Статус:</b> Активен\n"
            else:
                status_text += "⏳ <b>Статус:</b> Онбординг\n"

            if has_oauth:
                status_text += "✅ <b>Google OAuth:</b> Подключен\n"
            else:
                status_text += "❌ <b>Google OAuth:</b> Не подключен\n"

            if has_calendar:
                status_text += f"✅ <b>Календарь бота:</b> {escape(specialist.calendar_settings.calendar_summary or 'подключён')}\n"
                status_text += "✅ <b>Интеграция:</b> Успешно\n" if smoke_ok else "❌ <b>Интеграция:</b> Не завершена\n"
            else:
                status_text += "❌ <b>Календарь бота:</b> Не выбран\n"

            # Логика восстановления состояния (FSM)
            keyboard = None
            next_step_msg = ""
            new_state = None

            if specialist.status == SpecialistStatus.active and has_bot:
                await state.clear()
                personal_bot_username = active_bot.bot_username
                personal_link = _build_personal_deep_link(personal_bot_username)
                final_text = (
                    f"✅ Вы активны. Откройте личного бота: @{escape(personal_bot_username or '')}.\n\n"
                    "Через личного бота вы управляете настройками и проверяете статусы интеграций."
                )
                keyboard_rows = []
                if personal_link:
                    keyboard_rows.append([types.InlineKeyboardButton(text="🚀 Открыть личного бота", url=personal_link)])
                keyboard_rows.append([types.InlineKeyboardButton(text="🔁 Проверить интеграции", callback_data="calendar:smoke")])
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
                await _send_safe_html_message(message, final_text, reply_markup=keyboard)
                await log_outbound_message(
                    message.bot,
                    tg_user_id,
                    final_text,
                    fsm_state=None,
                    user_handle=user_handle,
                    specialist_name=specialist_name if has_profile else None,
                )
                return

            if not has_profile:
                await state.set_state(OnboardingStates.waiting_for_public_name)
                next_step_msg = "\n👇 <b>Действие:</b> Введите ваше публичное имя для клиентов."
                keyboard = types.ReplyKeyboardRemove()
                new_state = "waiting_for_public_name"
            
            elif not has_specialization:
                await state.set_state(OnboardingStates.waiting_for_specialization)
                next_step_msg = "\n👇 <b>Действие:</b> Укажите вашу специализацию."
                keyboard = types.ReplyKeyboardRemove()
                new_state = "waiting_for_specialization"

            elif not has_bot:
                await state.set_state(OnboardingStates.waiting_for_bot_token)
                next_step_msg = "\n👇 <b>Действие:</b> Пришлите токен вашего бота от @BotFather."
                keyboard = types.ReplyKeyboardRemove()
                new_state = "waiting_for_bot_token"

            elif not has_oauth:
                raw_token = await web_connect.create_connect_token(
                    session,
                    specialist.specialist_id,
                    tg_user_id,
                    ttl_minutes=15,
                )
                await session.commit()
                connect_url = _build_connect_page_url(raw_token)
                next_step_msg = (
                    "\n👇 <b>Действие:</b> Подключите Google аккаунт через кнопку ниже.\n"
                    "Откроется страница сайта. Подключение Google пройдет в браузере."
                )
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(text="Подключить Google Календарь", url=connect_url)
                    ]]
                )
                await state.clear()
                new_state = "waiting_for_oauth"

            elif has_calendar:
                await state.set_state(OnboardingStates.waiting_for_calendar_action)
                next_step_msg = "\n✅ Календарь уже подключён. Можно перепроверить доступ."
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔁 Проверить интеграцию", callback_data="calendar:smoke")],
                        [types.InlineKeyboardButton(text="📅 Сменить календарь", callback_data="calendar:switch_stub")],
                    ]
                )
                new_state = "calendar_connected"

            else:
                await state.set_state(OnboardingStates.waiting_for_calendar_action)
                next_step_msg = "\n👇 <b>Действие:</b> Выберите как подключить рабочий календарь бота."
                keyboard = _calendar_switch_keyboard(has_selected_calendar=has_calendar)
                new_state = "waiting_for_calendar_action"
            
            final_text = status_text + next_step_msg
            if _needs_personal_onboarding_prompt(specialist) and active_bot is not None:
                deep_link = _build_personal_deep_link(active_bot.bot_username)
                await _send_safe_html_message(
                    message,
                    "⏳ Онбординг ещё не завершён полностью. Перейдите в персональный бот, "
                    "чтобы подтвердить/изменить стартовые настройки.\n"
                    f"{deep_link if deep_link else 'Откройте вашего персонального бота по username.'}",
                    reply_markup=_full_onboarding_guard_keyboard(deep_link),
                )
            await _send_safe_html_message(message, final_text, reply_markup=keyboard)
            
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




@router.message(Command("video"))
async def cmd_video(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_handle = _get_handle(message.from_user)

    if not MASTER_ONBOARDING_VIDEO_FILE_ID:
        text_out = "Видео-инструкция пока недоступна."
        await message.answer(text_out)
        await log_outbound_message(
            message.bot,
            message.from_user.id,
            text_out,
            fsm_state=current_state,
            user_handle=user_handle,
        )
        return

    caption = "Видео-инструкция по подключению."
    await message.answer_video(
        video=MASTER_ONBOARDING_VIDEO_FILE_ID,
        caption=caption,
        reply_markup=_video_continue_keyboard(),
    )
    await log_outbound_message(
        message.bot,
        message.from_user.id,
        f"[video:{MASTER_ONBOARDING_VIDEO_FILE_ID}] {caption}",
        fsm_state=current_state,
        user_handle=user_handle,
    )


@router.callback_query(F.data == "video:continue")
async def video_continue(callback: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    user_handle = _get_handle(callback.from_user)

    try:
        text_out = await _send_onboarding_screen_for_state(callback, state, current_state)
        if text_out is not None:
            await log_outbound_message(
                callback.message.bot,
                callback.from_user.id,
                text_out,
                fsm_state=current_state,
                user_handle=user_handle,
            )
    finally:
        await callback.answer()

@router.callback_query(F.data.startswith("plan:pay_stub:"))
async def plan_pay_stub(callback: types.CallbackQuery):
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректный выбор тарифа.", show_alert=True)
        return

    _, _, plan_raw, period = parts
    try:
        plan = TariffPlan(plan_raw)
    except ValueError:
        await callback.answer("Некорректный выбор тарифа.", show_alert=True)
        return

    try:
        async with async_session_factory() as session:
            specialist = await ensure_specialist_with_profile_for_tg_user(
                session=session,
                tg_user_id=callback.from_user.id,
                tg_username=callback.from_user.username,
                tg_first_name=callback.from_user.first_name,
                tg_last_name=callback.from_user.last_name,
            )

        _, pay_url = await create_subscription_purchase(
            specialist.specialist_id,
            callback.from_user.id,
            plan,
            period,
        )
    except Exception:
        logger.exception("create_subscription_purchase failed")
        await callback.answer("Не удалось создать ссылку на оплату. Попробуйте позже.", show_alert=True)
        return

    card = _PLAN_CARD_CONTENT[plan]
    period_label = _PLAN_PERIOD_LABELS.get(period, "месяц")
    text_out = f"💳 Ссылка на оплату для тарифа <b>{card['title']}</b> ({period_label}) готова."
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Открыть страницу оплаты", url=pay_url)],
            [types.InlineKeyboardButton(text="Продолжить настройку", callback_data="onboarding:start")],
            [types.InlineKeyboardButton(text="Статус подписки", callback_data="plan:check_payment")],
        ]
    )
    await _send_safe_html_message(
        callback.message,
        text_out,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "plan:check_payment")
async def plan_check_payment(callback: types.CallbackQuery):
    status_text = await get_latest_purchase_status_text(callback.from_user.id)

    reply_markup = None
    if not await _is_master_onboarding_completed(callback.from_user.id):
        reply_markup = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Продолжить настройку", callback_data="onboarding:start")],
            ]
        )

    await callback.message.answer(status_text, reply_markup=reply_markup)
    await callback.answer()


@router.callback_query(F.data == "onboarding:start")
async def onboarding_start_from_plan(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    if await _is_master_onboarding_completed(callback.from_user.id):
        await cmd_start(callback.message, state)
        return

    prev_state = await state.get_state()
    await state.clear()
    await state.set_state(OnboardingStates.waiting_for_public_name)
    log_event(
        logger,
        logging.INFO,
        event="onboarding_step",
        specialist_id=None,
        tg_user_id=callback.from_user.id,
        from_state=prev_state,
        to_state=OnboardingStates.waiting_for_public_name.state,
        action="start_from_plan_preview",
        outcome="ok",
    )

    text_out = (
        "📝 **Шаг 1 из 5. Имя**\n\n"
        "Посмотреть видео-инструкцию: /video\n\n"
        "Введите имя, которое будут видеть ваши клиенты.\n"
        "Например: *Анна* или *Иван Иванов*."
    )
    await callback.message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
    await log_outbound_message(
        callback.message.bot,
        callback.from_user.id,
        text_out,
        fsm_state=OnboardingStates.waiting_for_public_name.state,
        user_handle=_get_handle(callback.from_user),
    )


@router.message(F.text == "🚀 Подключить сервис записи")
async def start_flow(message: types.Message, state: FSMContext):
    prev_state = await state.get_state()
    await state.set_state(OnboardingStates.waiting_for_public_name)
    log_event(
        logger,
        logging.INFO,
        event="onboarding_step",
        specialist_id=None,
        tg_user_id=message.from_user.id,
        from_state=prev_state,
        to_state=OnboardingStates.waiting_for_public_name.state,
        action="start",
        outcome="ok",
    )
    user_handle = _get_handle(message.from_user)
    
    text_out = (
        "📝 **Шаг 1 из 5. Имя**\n\n"
        "Посмотреть видео-инструкцию: /video\n\n"
        "Введите имя, которое будут видеть ваши клиенты.\n"
        "Например: *Анна* или *Иван Иванов*."
    )
    await message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
    await log_outbound_message(message.bot, message.from_user.id, text_out, fsm_state="waiting_for_public_name", user_handle=user_handle)


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    public_name = (message.text or "").strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    from_state = await state.get_state()

    if not _is_valid_public_name(public_name):
        reason = "too_short" if len(public_name) < 2 else "too_long"
        log_event(
            logger,
            logging.WARNING,
            event="onboarding_validation_error",
            tg_user_id=tg_user_id,
            stage="public_name",
            reason=reason,
            text_length=len(public_name),
        )
        text_out = (
            "⚠️ Некорректное публичное имя. Используйте от 2 до 80 символов.\n"
            "Пример: *Анна* или *Иван Иванов*."
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
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=None,
            tg_user_id=tg_user_id,
            from_state=from_state,
            to_state=OnboardingStates.waiting_for_public_name.state,
            action="public_name_retry",
            outcome="validation_error",
        )
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
                    session_duration_min=60,
                    session_buffer_min=10,
                )
                session.add(profile)
            else:
                profile.public_name = public_name
                profile.owner_tg_user_id = tg_user_id
                if profile.session_duration_min <= 0:
                    profile.session_duration_min = 60
                if profile.session_buffer_min < 0:
                    profile.session_buffer_min = 10
            await session.commit()

        await state.set_state(OnboardingStates.waiting_for_specialization)
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=str(auth_entry.specialist_id),
            tg_user_id=tg_user_id,
            from_state=from_state,
            to_state=OnboardingStates.waiting_for_specialization.state,
            action="public_name_submit",
            outcome="ok",
        )

        text_out = (
            f"✅ Имя сохранено: **{public_name}**\n\n"
            "🧩 **Шаг 2 из 5. Специализация**\n\n"
            "Укажите вашу специализацию.\n"
            "Например: *Психолог*, *Коуч*, *Психотерапевт*, *Репетитор*."
        )
        await message.answer(text_out)
        await log_outbound_message(
            message.bot, tg_user_id, text_out,
            fsm_state="waiting_for_specialization", user_handle=user_handle, specialist_name=public_name
        )

    except Exception:
        error_trace = traceback.format_exc()
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "process_public_name")
        await message.answer("⚠️ Ошибка сохранения имени. Попробуйте еще раз.")


@router.message(OnboardingStates.waiting_for_specialization)
async def process_specialization(message: types.Message, state: FSMContext):
    specialization = (message.text or "")
    # Normalize control chars to prevent log/message injection vectors.
    specialization = specialization.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    specialization = specialization.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    from_state = await state.get_state()

    if not _is_valid_specialization(specialization):
        text_out = (
            "⚠️ Некорректная специализация. Используйте от 2 до 120 символов: "
            "буквы, цифры, пробел, дефис или точку."
        )
        await message.answer(text_out)
        await log_outbound_message(
            message.bot,
            tg_user_id,
            text_out,
            fsm_state="waiting_for_specialization",
            user_handle=user_handle,
        )
        await state.set_state(OnboardingStates.waiting_for_specialization)
        log_event(
            logger,
            logging.WARNING,
            event="onboarding_validation_error",
            tg_user_id=tg_user_id,
            stage="specialization",
            reason="invalid_format",
            text_length=len(specialization),
        )
        return

    try:
        async with async_session_factory() as session:
            stmt = (
                select(Specialist)
                .join(SpecialistAuthTelegram, SpecialistAuthTelegram.specialist_id == Specialist.specialist_id)
                .where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            )
            specialist = (await session.execute(stmt)).scalar_one()
            specialist.specialization = specialization
            await session.commit()

        await state.set_state(OnboardingStates.waiting_for_bot_token)
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=str(specialist.specialist_id),
            tg_user_id=tg_user_id,
            from_state=from_state,
            to_state=OnboardingStates.waiting_for_bot_token.state,
            action="specialization_submit",
            outcome="ok",
        )

        text_out = (
            "✅ Специализация сохранена.\n\n"
            "🤖 **Шаг 3 из 5. Личный бот**\n\n"
            "1. Откройте @BotFather\n"
            "2. Создайте нового бота командой /newbot\n"
            "3. Скопируйте **API Token** и пришлите его сюда."
        )
        await message.answer(text_out)
        await log_outbound_message(
            message.bot,
            tg_user_id,
            text_out,
            fsm_state="waiting_for_bot_token",
            user_handle=user_handle,
        )
    except Exception:
        error_trace = traceback.format_exc()
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "process_specialization")
        await message.answer("⚠️ Ошибка сохранения специализации. Попробуйте еще раз.")


@router.message(OnboardingStates.waiting_for_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    raw_token = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    
    specialist_id = None
    specialist_name = None
    from_state = await state.get_state()

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
            log_event(
                logger,
                logging.WARNING,
                event="onboarding_validation_error",
                tg_user_id=tg_user_id,
                stage="bot_token",
                reason=e.__class__.__name__,
                token_length=len(raw_token),
            )
            text_out = f"❌ **Неверный токен**\nОшибка: `{e}`\nПроверьте токен и пришлите снова."
            await send_user_message(message, text_out, fsm_state="waiting_for_bot_token")
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

        await set_master_onboarding_completed(specialist_id)

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
            await notify_exception(
                where="handlers.master_onboarding.process_bot_token.webhook",
                exc=e,
                context={"specialist_id": str(specialist_id), "bot_id": bot_info.id},
                event=message,
                user_visible_text=text_out,
            )
            await send_user_message(message, text_out, fsm_state="waiting_for_bot_token")
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
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=str(specialist_id) if specialist_id else None,
            tg_user_id=tg_user_id,
            from_state=from_state,
            to_state=None,
            action="save_bot_token",
            outcome="ok",
        )
        
        async with async_session_factory() as session:
            raw_token = await web_connect.create_connect_token(
                session,
                specialist_id,
                tg_user_id,
                ttl_minutes=15,
            )
            await session.commit()
        connect_url = _build_connect_page_url(raw_token)

        status_line = "🟢 Статус специалиста: active." if is_active_now else "⏳ Статус специалиста: onboarding."
        text_out = (
            f"✅ Бот **@{escape_markdown_v2(bot_info.username)}** успешно подключен!\n"
            f"{status_line}\n\n"
            "📅 **Шаг 4 из 5:** Подключите Google аккаунт.\n\n"
            "Откроется страница сайта. Подключение Google пройдет в браузере."
        )
        
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(text="Подключить Google Календарь", url=connect_url)
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

    except Exception as exc:
        error_trace = traceback.format_exc()
        await _log_error_to_db(message.bot, tg_user_id, error_trace, "process_bot_token")
        text_out = "⚠️ Критическая ошибка при подключении бота."
        await notify_exception(
            where="handlers.master_onboarding.process_bot_token",
            exc=exc,
            context={"tg_user_id": tg_user_id},
            event=message,
            user_visible_text=text_out,
        )
        await send_user_message(message, text_out)


async def _calendar_select(callback: types.CallbackQuery, state: FSMContext):
    from_state = await state.get_state()
    try:
        await _start_calendar_select(callback, state)
        data = await state.get_data()
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=None,
            tg_user_id=callback.from_user.id,
            from_state=from_state,
            to_state=OnboardingStates.waiting_for_calendar_action.state,
            action="select_calendar",
            outcome="ok",
            calendars_count=len(data.get("cal_items") or []),
        )
    except GoogleCalendarInsufficientPermissionsError:
        await callback.message.answer(
            "⚠️ Google подключен, но доступов недостаточно для просмотра календарей и управления событиями. "
            "Переподключите через /start и подтвердите права: просмотр календарей и управление событиями."
        )
        await callback.answer()
    except GoogleCalendarError as exc:
        text_out = f"⚠️ Ошибка Google Calendar: {exc}"
        await notify_exception(
            where="handlers.master_onboarding.calendar_select.google",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
            user_visible_text=text_out,
        )
        await callback.message.answer(text_out)
        await callback.answer()
    except Exception as exc:
        logger.exception("calendar_select failed")
        text_out = "⚠️ Не удалось получить список календарей. Попробуйте позже."
        await notify_exception(
            where="handlers.master_onboarding.calendar_select",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
            user_visible_text=text_out,
        )
        await callback.message.answer(text_out)
        await callback.answer()


@router.callback_query(F.data == "calendar:refresh")
async def calendar_refresh(callback: types.CallbackQuery, state: FSMContext):
    try:
        await _start_calendar_select(callback, state)
    except GoogleCalendarInsufficientPermissionsError:
        await callback.message.answer(
            "⚠️ Google подключен, но доступов недостаточно для просмотра календарей и управления событиями. "
            "Переподключите через /start и подтвердите права: просмотр календарей и управление событиями."
        )
        await callback.answer()
    except GoogleCalendarError as exc:
        text_out = f"⚠️ Ошибка Google Calendar: {exc}"
        await notify_exception(
            where="handlers.master_onboarding.calendar_refresh.google",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
            user_visible_text=text_out,
        )
        await callback.message.answer(text_out)
        await callback.answer()
    except Exception as exc:
        logger.exception("calendar_refresh failed")
        text_out = "⚠️ Не удалось обновить список календарей. Попробуйте позже."
        await notify_exception(
            where="handlers.master_onboarding.calendar_refresh",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
            user_visible_text=text_out,
        )
        await callback.message.answer(text_out)
        await callback.answer()


@router.callback_query(F.data.startswith("calendar:page:"))
async def calendar_select_page(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    items = data.get("cal_items") or []
    per_page = int(data.get("cal_per_page") or 6)
    current_calendar_id = data.get("cal_current_calendar_id")
    if not items:
        await callback.message.answer("⚠️ Список календарей устарел. Нажмите /start и попробуйте снова.")
        await callback.answer()
        return

    try:
        page = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректная страница")
        return

    max_page = max(0, (len(items) - 1) // per_page)
    page = max(0, min(page, max_page))
    await state.update_data(cal_page=page)

    has_readonly = any(item.get("accessRole") == "reader" for item in items)
    await callback.message.edit_text(
        _calendar_select_text(len(items), page, per_page, has_readonly),
        reply_markup=_calendar_select_keyboard(items, page, per_page, current_calendar_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar:pick:"))
async def calendar_pick(callback: types.CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    data = await state.get_data()
    items = data.get("cal_items") or []
    picked_calendar_id: str | None = None
    specialist_id_for_context = None

    try:
        idx = int((callback.data or "").split(":")[-1])
    except ValueError:
        log_event(
            logger,
            logging.WARNING,
            event="onboarding_validation_error",
            tg_user_id=tg_user_id,
            stage="calendar_pick",
            reason="invalid_index",
        )
        await callback.answer("Некорректный выбор")
        return

    if idx < 0 or idx >= len(items):
        await callback.message.answer("⚠️ Выбранный календарь не найден. Откройте список заново через /start.")
        log_event(
            logger,
            logging.WARNING,
            event="onboarding_validation_error",
            tg_user_id=tg_user_id,
            stage="calendar_pick",
            reason="index_out_of_range",
        )
        await callback.answer()
        return

    calendar = items[idx]

    try:
        async with async_session_factory() as session:
            auth = (
                await session.execute(
                    select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
                )
            ).scalar_one_or_none()
            if not auth:
                await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
                await callback.answer()
                return

            specialist = (
                await session.execute(
                    select(Specialist)
                    .options(selectinload(Specialist.profile), selectinload(Specialist.calendar_settings))
                    .where(Specialist.specialist_id == auth.specialist_id)
                )
            ).scalar_one_or_none()

        if not specialist or not specialist.profile:
            await callback.message.answer("⚠️ Сначала заполните профиль через /start.")
            await callback.answer()
            return

        calendar_id = calendar.get("id")
        picked_calendar_id = calendar_id
        specialist_id_for_context = specialist.specialist_id
        summary = calendar.get("summary")
        calendar_tz = calendar.get("timeZone") or specialist.profile.specialist_timezone or "UTC"

        await _upsert_calendar_settings(
            specialist.specialist_id,
            calendar_id=calendar_id,
            calendar_summary=summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.selected,
        )

        smoke_ok = False
        try:
            await create_and_cleanup_test_event(specialist.specialist_id, calendar_id, calendar_tz)
            await _upsert_calendar_settings(
                specialist.specialist_id,
                calendar_id=calendar_id,
                calendar_summary=summary,
                calendar_tz=calendar_tz,
                source=SpecialistCalendarSource.selected,
                smoke_status="ok",
            )
            smoke_ok = True
        except Exception as smoke_exc:
            await _upsert_calendar_settings(
                specialist.specialist_id,
                calendar_id=calendar_id,
                calendar_summary=summary,
                calendar_tz=calendar_tz,
                source=SpecialistCalendarSource.selected,
                smoke_status="failed",
                smoke_error=str(smoke_exc)[:255],
            )
            await callback.message.answer(
                "❌ Календарь выбран, но интеграция не завершена. "
                "Проверьте права доступа к календарю и нажмите «Проверить интеграцию»."
            )

        if smoke_ok:
            try:
                await ensure_calendar_watch(specialist.specialist_id, calendar_id)
            except Exception:
                log_event(
                    logger,
                    logging.WARNING,
                    event="calendar_watch_setup_failed",
                    alias="master_onboarding_calendar_pick_ensure_watch",
                    specialist_id=str(specialist.specialist_id),
                    tg_user_id=tg_user_id,
                    calendar_id=calendar_id,
                )

        if smoke_ok:
            await finalize_specialist_if_ready(specialist.specialist_id)
            await state.clear()
            log_event(
                logger,
                logging.INFO,
                event="onboarding_step",
                specialist_id=str(specialist.specialist_id),
                tg_user_id=tg_user_id,
                from_state=OnboardingStates.waiting_for_calendar_action.state,
                to_state=None,
                action="select_calendar",
                outcome="ok",
            )

            deep_link = ""
            personal_username = None
            post_actions_failed = False
            try:
                personal_username = await _notify_personal_bot_welcome(specialist.specialist_id, tg_user_id)
                deep_link = _build_personal_deep_link(personal_username)
            except Exception as post_exc:
                post_actions_failed = True
                logger.warning(
                    "calendar_pick post actions failed specialist_id=%s tg_user_id=%s",
                    specialist.specialist_id,
                    tg_user_id,
                    exc_info=True,
                )
                await notify_exception(
                    where="handlers.master_onboarding.calendar_pick.post_actions",
                    exc=post_exc,
                    context={"tg_user_id": tg_user_id, "specialist_id": str(specialist.specialist_id)},
                    event=callback,
                )

            if post_actions_failed:
                await _answer_plain(
                    callback.message,
                    "✅ Календарь подключён. Если личный бот не открылся автоматически — откройте его вручную.",
                )
            else:
                text_out = (
                    "✅ Календарь подключён. Master-онбординг завершён.\n"
                    "Чтобы завершить онбординг полностью, перейдите в персональный бот и подтвердите/настройте параметры:\n"
                    f"@{personal_username}"
                )
                await _answer_plain(callback.message, text_out)

        await callback.answer()
    except Exception as exc:
        logger.exception("calendar_pick failed")
        if picked_calendar_id is not None:
            text_out = (
                "✅ Календарь выбран/подключён, но произошла ошибка на финальном шаге. "
                "Продолжайте в личном боте; если он не открылся автоматически — откройте вручную."
            )
            await notify_exception(
                where="handlers.master_onboarding.calendar_pick.post_pick_unexpected",
                exc=exc,
                context={
                    "tg_user_id": callback.from_user.id,
                    "specialist_id": str(specialist_id_for_context) if specialist_id_for_context else None,
                    "calendar_id": picked_calendar_id,
                },
                event=callback,
            )
            await _answer_plain(callback.message, text_out)
        else:
            text_out = "⚠️ Не удалось применить выбранный календарь. Попробуйте позже."
            await notify_exception(
                where="handlers.master_onboarding.calendar_pick",
                exc=exc,
                context={"tg_user_id": callback.from_user.id, "specialist_id": str(specialist_id_for_context) if specialist_id_for_context else None},
                event=callback,
            )
            await callback.message.answer(text_out)
        await callback.answer()


@router.callback_query(F.data == "calendar:cancel_select")
async def calendar_select_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_start(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "calendar:switch_stub")
async def calendar_switch_stub(callback: types.CallbackQuery, state: FSMContext):
    await _calendar_select(callback, state)


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
        now = datetime.now(timezone.utc)

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
        stmt = (
            select(TelegramBot)
            .where(
                TelegramBot.specialist_id == specialist_id,
                TelegramBot.status == TelegramBotStatus.active,
            )
            .order_by(TelegramBot.updated_at.desc(), TelegramBot.created_at.desc())
        )
        personal_bot = (await session.execute(stmt)).scalars().first()

    if not personal_bot:
        logger.info("No active personal bot found for welcome: specialist_id=%s", specialist_id)
        return None

    bot_token = decrypt_token(personal_bot.bot_token_encrypted)
    personal = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    retries = 2
    timeout_sec = 6.0
    retry_after_cap_sec = 4.0

    try:
        for attempt in range(retries + 1):
            try:
                await personal.send_message(
                    chat_id=tg_user_id,
                    text="🎉 Личный бот готов к работе. /start",
                    request_timeout=timeout_sec,
                )
                break
            except TelegramRetryAfter as exc:
                if attempt >= retries:
                    logger.warning(
                        "Failed to send welcome after retry_after: specialist_id=%s bot_user_id=%s bot_username=%s attempts=%s",
                        specialist_id,
                        personal_bot.bot_user_id,
                        personal_bot.bot_username,
                        attempt + 1,
                        exc_info=True,
                    )
                    break

                retry_after = max(0.0, min(float(getattr(exc, "retry_after", 1.0)), retry_after_cap_sec))
                logger.warning(
                    "Retrying welcome after TelegramRetryAfter: specialist_id=%s bot_user_id=%s bot_username=%s attempt=%s wait=%.2fs",
                    specialist_id,
                    personal_bot.bot_user_id,
                    personal_bot.bot_username,
                    attempt + 1,
                    retry_after,
                )
                await asyncio.sleep(retry_after)
            except (TelegramNetworkError, TelegramServerError, TimeoutError, asyncio.TimeoutError):
                if attempt >= retries:
                    logger.warning(
                        "Failed to send welcome due to retryable error: specialist_id=%s bot_user_id=%s bot_username=%s attempts=%s",
                        specialist_id,
                        personal_bot.bot_user_id,
                        personal_bot.bot_username,
                        attempt + 1,
                        exc_info=True,
                    )
                    break

                logger.warning(
                    "Retrying welcome due to retryable error: specialist_id=%s bot_user_id=%s bot_username=%s attempt=%s",
                    specialist_id,
                    personal_bot.bot_user_id,
                    personal_bot.bot_username,
                    attempt + 1,
                    exc_info=True,
                )
            except Exception:
                logger.warning(
                    "Failed to send welcome due to non-retryable error: specialist_id=%s bot_user_id=%s bot_username=%s",
                    specialist_id,
                    personal_bot.bot_user_id,
                    personal_bot.bot_username,
                    exc_info=True,
                )
                break
    finally:
        await personal.session.close()

    return personal_bot.bot_username


@router.callback_query(F.data == "calendar:create")
async def calendar_create(callback: types.CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    created_calendar_id: str | None = None
    created_calendar_summary: str | None = None
    specialist_id_for_context = None
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

        tz_for_create = await resolve_tz_for_calendar_creation(
            specialist_id=specialist.specialist_id,
            profile_tz=profile.specialist_timezone,
        )
        calendar = await create_bot_calendar(specialist.specialist_id, profile.public_name, tz_for_create)
        calendar_id = calendar.get("id")
        summary = calendar.get("summary")
        created_calendar_id = calendar_id
        created_calendar_summary = summary
        specialist_id_for_context = specialist.specialist_id
        calendar_tz = (calendar.get("timeZone") or tz_for_create or "UTC").strip() or "UTC"

        async with async_session_factory() as session:
            await apply_specialist_defaults_if_missing(
                session,
                specialist.specialist_id,
                preferred_timezone=calendar_tz,
            )
            await session.commit()

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
                "❌ Календарь создан, но интеграция не завершена: не пройдена проверка интеграции. "
                "Проверьте права Google и переподключите аккаунт."
            )
            await callback.answer()
            return

        try:
            await ensure_calendar_watch(specialist.specialist_id, calendar_id)
        except Exception:
            log_event(
                logger,
                logging.WARNING,
                event="calendar_watch_setup_failed",
                alias="master_onboarding_calendar_create_ensure_watch",
                specialist_id=str(specialist.specialist_id),
                tg_user_id=tg_user_id,
                calendar_id=calendar_id,
            )

        await finalize_specialist_if_ready(specialist.specialist_id)
        await state.clear()
        log_event(
            logger,
            logging.INFO,
            event="onboarding_step",
            specialist_id=str(specialist.specialist_id),
            tg_user_id=tg_user_id,
            from_state=OnboardingStates.waiting_for_calendar_action.state,
            to_state=None,
            action="create_calendar",
            outcome="ok",
        )

        deep_link = ""
        personal_username = None
        post_actions_failed = False
        try:
            personal_username = await _notify_personal_bot_welcome(specialist.specialist_id, tg_user_id)
            deep_link = _build_personal_deep_link(personal_username)
        except Exception as post_exc:
            post_actions_failed = True
            logger.warning(
                "calendar_create post actions failed specialist_id=%s tg_user_id=%s",
                specialist.specialist_id,
                tg_user_id,
                exc_info=True,
            )
            await notify_exception(
                where="handlers.master_onboarding.calendar_create.post_actions",
                exc=post_exc,
                context={"tg_user_id": tg_user_id, "specialist_id": str(specialist.specialist_id)},
                event=callback,
            )

        if post_actions_failed:
            await _answer_plain(
                callback.message,
                "✅ Календарь подключён. Если личный бот не открылся автоматически — откройте его вручную."
            )
        else:
            await _answer_plain(
                callback.message,
                "✅ Календарь подключён. Master-онбординг завершён.\n"
                "Чтобы завершить онбординг полностью, перейдите в персональный бот и подтвердите/настройте параметры:\n"
                f"@{personal_username}"
            )
        await callback.answer()

    except GoogleCalendarInsufficientPermissionsError:
        await callback.message.answer(
            "⚠️ Недостаточно прав Google для выполнения операции. "
            "Нужны права: просмотр календарей и управление событиями. "
            "Переподключите через /start и подтвердите эти права."
        )
        await callback.answer()
    except GoogleCalendarError as exc:
        logger.exception("Google calendar operation failed")
        text_out = f"⚠️ Ошибка Google Calendar: {exc}"
        await notify_exception(
            where="handlers.master_onboarding.calendar_create.google",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
        )
        await callback.message.answer(text_out)
        await callback.answer()
    except Exception as exc:
        logger.exception("calendar_create failed")
        if created_calendar_id is not None:
            text_out = (
                "✅ Календарь создан/подключён, но произошла ошибка на финальном шаге. "
                "Если личный бот не открылся автоматически — откройте его вручную и продолжайте настройку."
            )
            await notify_exception(
                where="handlers.master_onboarding.calendar_create.post_create_unexpected",
                exc=exc,
                context={
                    "tg_user_id": callback.from_user.id,
                    "specialist_id": str(specialist_id_for_context) if specialist_id_for_context else None,
                    "calendar_id": created_calendar_id,
                    "calendar_summary": created_calendar_summary,
                },
                event=callback,
            )
            await _answer_plain(callback.message, text_out)
        else:
            text_out = "⚠️ Не удалось подключить календарь. Попробуйте позже."
            await notify_exception(
                where="handlers.master_onboarding.calendar_create",
                exc=exc,
                context={"tg_user_id": callback.from_user.id, "specialist_id": str(specialist_id_for_context) if specialist_id_for_context else None},
                event=callback,
            )
            await callback.message.answer(text_out)
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
        await callback.message.answer("✅ Интеграция успешно выполнена.")
        await callback.answer()
    except Exception as exc:
        async with async_session_factory() as session:
            auth = (await session.execute(select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id))).scalar_one_or_none()
            settings = None
            if auth:
                settings = (await session.execute(select(SpecialistCalendarSettings).where(SpecialistCalendarSettings.specialist_id == auth.specialist_id))).scalar_one_or_none()
                if settings:
                    settings.last_smoke_test_status = "failed"
                    settings.last_smoke_test_at = datetime.now(timezone.utc)
                    settings.last_smoke_test_error = str(exc)[:255]
                    await session.commit()

        await callback.message.answer("❌ Интеграция не завершена. Проверьте права Google и переподключите аккаунт.")
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


@router.callback_query(F.data == "full_onboarding:recheck")
async def full_onboarding_recheck(callback: types.CallbackQuery):
    tg_user_id = callback.from_user.id
    try:
        specialist = await get_specialist_by_tg_user_id(tg_user_id)
        if specialist is None:
            await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
            await callback.answer()
            return

        async with async_session_factory() as session:
            bot = (
                await session.execute(
                    select(TelegramBot)
                    .where(
                        TelegramBot.specialist_id == specialist.specialist_id,
                        TelegramBot.status == TelegramBotStatus.active,
                    )
                    .order_by(TelegramBot.created_at.desc())
                )
            ).scalars().first()

        if specialist.onboarding_personal_completed_at is not None:
            await callback.message.answer("✅ Полный онбординг уже завершён. Можно продолжать работу в master-боте.")
        else:
            username = bot.bot_username if bot else None
            deep_link = _build_personal_deep_link(username)
            await callback.message.answer(
                "⏳ Онбординг ещё не завершён. Завершите его в персональном боте:\n"
                f"{deep_link if deep_link else 'Откройте персональный бот по username.'}",
                reply_markup=_full_onboarding_guard_keyboard(deep_link),
            )
        await callback.answer()
    except Exception as exc:
        logger.exception("full_onboarding_recheck failed tg_user_id=%s", tg_user_id)
        text_out = "⚠️ Не удалось проверить статус онбординга. Попробуйте позже."
        await notify_exception(
            where="handlers.master_onboarding.full_onboarding_recheck",
            exc=exc,
            context={"tg_user_id": tg_user_id},
            event=callback,
            user_visible_text=text_out,
        )
        await callback.message.answer(text_out)
        await callback.answer()
