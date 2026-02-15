import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import SUPPORT_TG_URL
from database import Client, ClientTimezoneSource, Specialist, SpecialistProfile, async_session_factory
from handlers.personal_bot.routers.specialist.owner_panel import send_owner_panel
from services.specialist_defaults import apply_specialist_defaults_if_missing
from services.log_context import log_event

router = Router(name="personal_bot_common_start")
logger = logging.getLogger(__name__)


def _log_personal_handler(*, handler_name: str, bot_id, tg_user_id: int | None, fsm_state: str | None, outcome: str, update_type: str, text_length: int | None = None) -> None:
    log_event(
        logger,
        logging.INFO,
        event="personal_handler",
        bot_id=bot_id,
        tg_user_id=tg_user_id,
        handler_name=handler_name,
        fsm_state=fsm_state,
        outcome=outcome,
        update_type=update_type,
        text_length=text_length,
    )


def _fallback_public_name(message: Message, public_name: str | None) -> str:
    if public_name and public_name.strip():
        return public_name.strip()
    if message.from_user:
        if message.from_user.full_name:
            return message.from_user.full_name
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        return f"{first_name} {last_name}".strip() or "Специалист"
    return "Специалист"


def _onboarding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить настройки", callback_data="onboarding:change")],
            [InlineKeyboardButton(text="👌 Оставить как есть", callback_data="onboarding:keep")],
            [InlineKeyboardButton(text="Позже", callback_data="onboarding:later")],
        ]
    )


def _onboarding_keyboard_with_calendar() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Изменить календарь", callback_data="calendar:switch_stub")],
            [InlineKeyboardButton(text="✏️ Изменить настройки", callback_data="onboarding:change")],
            [InlineKeyboardButton(text="👌 Оставить как есть", callback_data="onboarding:keep")],
            [InlineKeyboardButton(text="Позже", callback_data="onboarding:later")],
        ]
    )


def _client_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записаться")],
            [KeyboardButton(text="Мои записи (пока stub)")],
            [KeyboardButton(text="Сменить часовой пояс (пока stub)")],
        ],
        resize_keyboard=True,
    )


async def _ensure_client_exists(*, specialist_id, tg_user_id: int, tg_username: str | None) -> Client | None:
    async with async_session_factory() as session:
        if specialist_id is None:
            return None

        existing = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()

        if existing is not None:
            if existing.tg_username != tg_username:
                existing.tg_username = tg_username
                await session.commit()
            return existing

        client = Client(
            specialist_id=specialist_id,
            tg_user_id=tg_user_id,
            tg_username=tg_username,
            display_name=None,
            client_code=f"tg-{tg_user_id}",
            client_timezone="UTC",
            timezone_source=ClientTimezoneSource.default_from_specialist,
        )
        session.add(client)
        await session.commit()
        await session.refresh(client)
        return client


async def _load_specialist_and_profile(specialist_id):
    async with async_session_factory() as session:
        specialist = (
            await session.execute(
                select(Specialist)
                .options(selectinload(Specialist.profile), selectinload(Specialist.calendar_settings))
                .where(Specialist.specialist_id == specialist_id)
            )
        ).scalar_one_or_none()
        profile = specialist.profile if specialist else await session.get(SpecialistProfile, specialist_id)
    return specialist, profile


async def _ensure_defaults_exist(specialist_id) -> None:
    async with async_session_factory() as session:
        await apply_specialist_defaults_if_missing(session, specialist_id)
        await session.commit()


async def _render_onboarding_screen(message: Message, specialist_id) -> None:
    await _ensure_defaults_exist(specialist_id)
    specialist, profile = await _load_specialist_and_profile(specialist_id)

    if specialist is None:
        await message.answer(
            "⚠️ Профиль специалиста не найден. Вернитесь в master-бот и повторите онбординг. "
            f"Поддержка: {SUPPORT_TG_URL}"
        )
        return

    if profile is None:
        await message.answer(
            "⚠️ Не удалось загрузить настройки профиля. Попробуйте позже или обратитесь в поддержку: "
            f"{SUPPORT_TG_URL}"
        )
        return

    calendar_settings = getattr(specialist, "calendar_settings", None)
    current_calendar_lines = ["Текущий календарь: не выбран"]
    if calendar_settings and getattr(calendar_settings, "calendar_id", None):
        smoke_status = getattr(calendar_settings, "last_smoke_test_status", None)
        if smoke_status not in {"ok", "failed"}:
            smoke_status = "unknown"
        current_calendar_lines = [
            f"Текущий календарь: {calendar_settings.calendar_summary or calendar_settings.calendar_id}",
            f"Часовой пояс: {calendar_settings.calendar_time_zone or 'UTC'}",
            f"Smoke-test: {smoke_status}",
        ]

    text = (
        "🧩 Продолжим онбординг в персональном боте.\n\n"
        "Настройки по умолчанию:\n"
        f"• Длительность сессии: {profile.session_duration_min} мин\n"
        f"• Перерыв между сессиями: {profile.session_buffer_min} мин\n"
        f"• Часовой пояс: {profile.specialist_timezone or 'UTC'}\n"
        f"• Макс. сессий в день: {profile.max_sessions_per_day}\n"
        f"• Шаг слотов: {profile.slot_step_min} мин\n"
        f"• Окно отмены: {profile.cancel_window_hours} ч\n\n"
        f"{chr(10).join(current_calendar_lines)}\n\n"
        "Подтвердите настройки или измените их перед завершением онбординга."
    )
    await message.answer(text, reply_markup=_onboarding_keyboard_with_calendar())


@router.message(CommandStart())
async def personal_start(
    message: Message,
    command: CommandObject,
    actor: str,
    specialist_id,
    public_name: str | None,
    owner_tg_user_id: int | None,
) -> None:
    _log_personal_handler(
        handler_name="personal_start",
        bot_id=message.bot.id,
        tg_user_id=message.from_user.id if message.from_user else None,
        fsm_state=None,
        outcome="start",
        update_type="message",
        text_length=len(message.text or ""),
    )
    if actor == "specialist":
        resolved_public_name = _fallback_public_name(message, public_name)
        resolved_owner_tg_user_id = owner_tg_user_id or (message.from_user.id if message.from_user else None)

        if specialist_id is None:
            logger.error(
                "personal_start: missing specialist_id for actor=specialist, tg_user_id=%s",
                resolved_owner_tg_user_id,
            )
            await message.answer(
                "⚠️ Не удалось определить профиль специалиста для этого бота. "
                "Вернитесь в master-бот и завершите онбординг заново, либо обратитесь в поддержку: "
                f"{SUPPORT_TG_URL}"
            )
            return

        try:
            specialist, _ = await _load_specialist_and_profile(specialist_id)
            if specialist is None:
                await message.answer(
                    "⚠️ Профиль специалиста не найден. Вернитесь в master-бот и завершите онбординг заново. "
                    f"Поддержка: {SUPPORT_TG_URL}"
                )
                return

            logger.info(
                "personal_start actor=%s specialist_id=%s command_args=%s onboarding_master=%s onboarding_personal=%s",
                actor,
                specialist_id,
                command.args,
                specialist.onboarding_master_completed_at,
                specialist.onboarding_personal_completed_at,
            )

            if specialist.onboarding_personal_completed_at is None:
                if command.args and command.args not in {"owner_panel", "onboarding"}:
                    await message.answer("ℹ️ Неизвестный старт-параметр. Продолжаем онбординг.")
                await _render_onboarding_screen(message, specialist_id)
                return

            if command.args and command.args != "owner_panel":
                await message.answer("ℹ️ Неизвестный старт-параметр. Открываю панель специалиста.")

            await send_owner_panel(
                message=message,
                specialist_id=specialist_id,
                public_name=resolved_public_name,
                owner_tg_user_id=resolved_owner_tg_user_id,
            )

        except Exception:
            logger.exception(
                "personal_start failed, specialist_id=%s, tg_user_id=%s",
                specialist_id,
                resolved_owner_tg_user_id,
            )
            await message.answer(
                "⚠️ Возникла ошибка при открытии панели. Попробуйте еще раз или напишите в поддержку."
            )
            return

        await message.answer(
            "Доступно сейчас:\n"
            "• /status — состояние интеграций\n"
            "• /help — список команд\n\n"
            f"Поддержка: {SUPPORT_TG_URL}"
        )
        return

    if message.from_user is None:
        await message.answer("⚠️ Не удалось определить пользователя Telegram. Попробуйте ещё раз.")
        return

    try:
        client = await _ensure_client_exists(
            specialist_id=specialist_id,
            tg_user_id=message.from_user.id,
            tg_username=message.from_user.username,
        )
        if client is None:
            await message.answer("⚠️ Не удалось определить специалиста для этого бота.")
            return

        if not (client.display_name and client.display_name.strip()):
            await message.answer("👋 Добро пожаловать! Как к вам обращаться?")
            return

        await message.answer("Меню клиента:", reply_markup=_client_menu_keyboard())
    except Exception:
        logger.exception("personal_start: failed to render client menu")


@router.callback_query(F.data == "onboarding:keep")
async def onboarding_keep(callback: CallbackQuery, specialist_id, public_name: str | None, owner_tg_user_id: int | None) -> None:
    _log_personal_handler(
        handler_name="onboarding_keep",
        bot_id=callback.bot.id,
        tg_user_id=callback.from_user.id if callback.from_user else None,
        fsm_state=None,
        outcome="start",
        update_type="callback_query",
    )
    try:
        async with async_session_factory() as session:
            specialist = await session.get(Specialist, specialist_id)
            if specialist is None:
                await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start в master-боте.")
                await callback.answer()
                return
            specialist.onboarding_personal_completed_at = datetime.now(timezone.utc)
            await session.commit()

        await callback.message.answer("✅ Отлично, онбординг завершён. Открываю панель специалиста.")
        try:
            await send_owner_panel(
                message=callback.message,
                specialist_id=specialist_id,
                public_name=public_name,
                owner_tg_user_id=owner_tg_user_id,
            )
        except Exception:
            logger.exception("onboarding_keep send_owner_panel failed specialist_id=%s", specialist_id)
            await callback.message.answer("⚠️ Возникла ошибка при открытии панели. Попробуйте еще раз или напишите в поддержку.")
        await callback.answer()
    except Exception:
        logger.exception("onboarding_keep failed specialist_id=%s", specialist_id)
        await callback.message.answer(f"⚠️ Не удалось завершить онбординг. Поддержка: {SUPPORT_TG_URL}")
        await callback.answer()


@router.callback_query(F.data == "onboarding:change")
async def onboarding_change(callback: CallbackQuery, specialist_id, public_name: str | None, owner_tg_user_id: int | None) -> None:
    _log_personal_handler(
        handler_name="onboarding_change",
        bot_id=callback.bot.id,
        tg_user_id=callback.from_user.id if callback.from_user else None,
        fsm_state=None,
        outcome="start",
        update_type="callback_query",
    )
    try:
        await callback.message.answer(
            "✏️ Откройте панель и измените параметры. После этого нажмите «👌 Оставить как есть» в онбординге.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Открыть панель настроек", callback_data="owner_panel:change_duration_buffer")]]
            ),
        )
        await send_owner_panel(
            message=callback.message,
            specialist_id=specialist_id,
            public_name=public_name,
            owner_tg_user_id=owner_tg_user_id,
        )
        await callback.answer()
    except Exception:
        logger.exception("onboarding_change failed specialist_id=%s", specialist_id)
        await callback.message.answer(f"⚠️ Не удалось открыть настройки. Поддержка: {SUPPORT_TG_URL}")
        await callback.answer()


@router.callback_query(F.data == "onboarding:later")
async def onboarding_later(callback: CallbackQuery) -> None:
    _log_personal_handler(
        handler_name="onboarding_later",
        bot_id=callback.bot.id,
        tg_user_id=callback.from_user.id if callback.from_user else None,
        fsm_state=None,
        outcome="start",
        update_type="callback_query",
    )
    try:
        await callback.message.answer(
            "⏳ Вы можете завершить онбординг позже. В master-боте часть функций пока будет недоступна. "
            "Когда будете готовы, вернитесь и нажмите /start здесь снова."
        )
        await callback.answer()
    except Exception:
        logger.exception("onboarding_later failed")
        await callback.message.answer(f"⚠️ Не удалось обработать действие. Поддержка: {SUPPORT_TG_URL}")
        await callback.answer()
