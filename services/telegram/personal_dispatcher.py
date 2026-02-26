import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject, Update
from sqlalchemy import select

from config import SUPPORT_TG_URL
from database import SpecialistAuthTelegram, SpecialistProfile, TelegramBot, async_session_factory
from handlers.personal_bot import router as personal_router
from handlers.personal_bot.routers.common import start as start_router
from services.alerting import notify_exception
from services.telegram.bot_factory import get_personal_bot

logger = logging.getLogger(__name__)

_personal_dispatcher: Dispatcher | None = None
_profile_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_PROFILE_TTL_SEC = 10.0
_profile_cache_lock = asyncio.Lock()


def _get_sender_id(update: Update) -> int | None:
    if update.message and update.message.from_user:
        return update.message.from_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    if update.edited_message and update.edited_message.from_user:
        return update.edited_message.from_user.id
    if update.inline_query and update.inline_query.from_user:
        return update.inline_query.from_user.id
    if update.my_chat_member and update.my_chat_member.from_user:
        return update.my_chat_member.from_user.id
    if update.chat_member and update.chat_member.from_user:
        return update.chat_member.from_user.id
    return None


async def _load_specialist_profile(specialist_id) -> dict[str, Any] | None:
    cache_key = str(specialist_id)
    now = time.monotonic()
    async with _profile_cache_lock:
        cached = _profile_cache.get(cache_key)
        if cached and now < cached[0]:
            return cached[1]

    async with async_session_factory() as session:
        stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == specialist_id)
        profile = (await session.execute(stmt)).scalar_one_or_none()

    if profile is None:
        async with _profile_cache_lock:
            _profile_cache.pop(cache_key, None)
        return None

    data = {
        "owner_tg_user_id": profile.owner_tg_user_id,
        "public_name": profile.public_name,
    }
    async with _profile_cache_lock:
        _profile_cache[cache_key] = (now + _PROFILE_TTL_SEC, data)
    return data


class PersonalContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update = event if isinstance(event, Update) else None
        tg_bot: TelegramBot | None = data.get("telegram_bot")

        data["actor"] = "client"
        data["specialist_id"] = tg_bot.specialist_id if tg_bot is not None else None
        data["owner_tg_user_id"] = None
        data["public_name"] = None

        if update is not None and tg_bot is not None and tg_bot.specialist_id is not None:
            profile = await _load_specialist_profile(tg_bot.specialist_id)
            sender_id = _get_sender_id(update)
            auth_tg_user_id = await _load_specialist_auth_tg_user_id(tg_bot.specialist_id)

            if profile is not None:
                data["owner_tg_user_id"] = profile["owner_tg_user_id"]
                data["public_name"] = profile["public_name"]
            if data["owner_tg_user_id"] is None:
                data["owner_tg_user_id"] = auth_tg_user_id

            if sender_id is not None and data["owner_tg_user_id"] is not None and sender_id == data["owner_tg_user_id"]:
                data["actor"] = "specialist"

        return await handler(event, data)


async def _load_specialist_auth_tg_user_id(specialist_id) -> int | None:
    async with async_session_factory() as session:
        stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.specialist_id == specialist_id)
        auth = (await session.execute(stmt)).scalar_one_or_none()
    return getattr(auth, "tg_user_id", None) if auth is not None else None


async def _extract_fsm_state_name(data: dict[str, Any]) -> str | None:
    state_ctx = data.get("state")
    if state_ctx is None or not hasattr(state_ctx, "get_state"):
        return None
    try:
        state_name = await state_ctx.get_state()
    except Exception:
        return None
    return str(state_name) if state_name else None


def _extract_handler_name(data: dict[str, Any]) -> str | None:
    handler_obj = data.get("handler")
    if handler_obj is None:
        return None
    callback = getattr(handler_obj, "callback", None)
    if callback is None:
        return getattr(handler_obj, "__name__", None)
    return getattr(callback, "__name__", None)


class PersonalGlobalErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except PersonalExpectedUXError as exc:
            update = event if isinstance(event, Update) else None
            await self._handle_expected_ux_error(update=update, data=data, exc=exc)
            return None
        except Exception as exc:
            update = event if isinstance(event, Update) else None
            await self._handle_unexpected_error(update=update, data=data, exc=exc)
            return None

    async def _handle_expected_ux_error(self, *, update: Update | None, data: dict[str, Any], exc: Exception) -> None:
        tg_bot: TelegramBot | None = data.get("telegram_bot")
        handler_name = _extract_handler_name(data)
        fsm_state = await _extract_fsm_state_name(data)
        logger.info(
            "personal bot expected ux error update_id=%s bot_id=%s specialist_id=%s handler=%s fsm_state=%s error=%s",
            update.update_id if update else None,
            getattr(tg_bot, "bot_user_id", None),
            getattr(tg_bot, "specialist_id", None),
            handler_name,
            fsm_state,
            exc.__class__.__name__,
        )
        await self._reply_expected_ux_error(
            update=update,
            actor=str(data.get("actor") or "client"),
            specialist_id=data.get("specialist_id"),
        )

    async def _handle_unexpected_error(self, *, update: Update | None, data: dict[str, Any], exc: Exception) -> None:
        tg_bot: TelegramBot | None = data.get("telegram_bot")
        bot_username = getattr(tg_bot, "bot_username", None)
        bot_user_id = getattr(tg_bot, "bot_user_id", None)
        specialist_id = getattr(tg_bot, "specialist_id", None)
        handler_name = _extract_handler_name(data)
        fsm_state = await _extract_fsm_state_name(data)
        logger.error(
            "personal bot unhandled exception update_id=%s bot_username=%s bot_id=%s specialist_id=%s handler=%s fsm_state=%s",
            update.update_id if update else None,
            bot_username,
            bot_user_id,
            specialist_id,
            handler_name,
            fsm_state,
            exc_info=True,
        )
        await notify_exception(
            "services.telegram.personal_dispatcher.PersonalGlobalErrorMiddleware",
            exc,
            {
                "update_id": update.update_id if update else None,
                "bot_username": bot_username,
                "bot_id": bot_user_id,
                "specialist_id": str(specialist_id) if specialist_id is not None else None,
                "handler": handler_name,
                "fsm_state": fsm_state,
            },
            stage="runtime",
        )
        await self._reply_unexpected_error(update=update)

    async def _reply_expected_ux_error(self, *, update: Update | None, actor: str, specialist_id=None) -> None:
        if update is None:
            return
        message = update.message or (update.callback_query.message if update.callback_query else None)
        if message is None or message.chat.type != "private":
            return
        if update.callback_query is not None:
            try:
                await update.callback_query.answer()
            except Exception:
                logger.exception("failed to answer callback in expected ux error")
        try:
            await message.answer("Похоже, Вы начали не с /start. Нажмите /start или ‘🏠 В меню’.")
            if actor == "specialist":
                await message.answer(
                    "Меню специалиста:",
                    reply_markup=start_router._specialist_quick_menu_keyboard(has_selected_calendar=True),
                )
            else:
                await start_router.render_client_menu(
                    message,
                    where="personal_global_error_middleware:expected_ux",
                    specialist_id=specialist_id,
                    bot_user_id=getattr(getattr(message, "bot", None), "id", None),
                )
        except Exception:
            logger.exception("personal bot failed to send expected UX recovery reply")

    async def _reply_unexpected_error(self, *, update: Update | None) -> None:
        if update is None:
            return
        message = update.message or (update.callback_query.message if update.callback_query else None)
        if message is None or message.chat.type != "private":
            return
        if update.callback_query is not None:
            try:
                await update.callback_query.answer()
            except Exception:
                logger.exception("failed to answer callback in unexpected error")
        try:
            await message.answer(
                "⚠️ Произошла ошибка при обработке команды. Попробуйте еще раз или обратитесь в поддержку: "
                f"{SUPPORT_TG_URL}"
            )
        except Exception:
            logger.exception("personal bot failed to send generic error reply update_id=%s", update.update_id)


class PersonalExpectedUXError(Exception):
    """Base class for expected personal-bot UX flow exceptions."""


class UnknownIntentError(PersonalExpectedUXError):
    """Raised when text/command is outside current known intent."""


class InvalidCallbackError(PersonalExpectedUXError):
    """Raised when callback payload is invalid for current flow."""


class StateMismatchError(PersonalExpectedUXError):
    """Raised when FSM state does not match the requested action."""


def get_personal_dispatcher() -> Dispatcher:
    global _personal_dispatcher
    if _personal_dispatcher is None:
        dp = Dispatcher()
        dp.update.outer_middleware(PersonalGlobalErrorMiddleware())
        dp.update.middleware(PersonalContextMiddleware())
        dp.include_router(personal_router)
        _personal_dispatcher = dp
    return _personal_dispatcher


def build_bot_from_db(telegram_bot: TelegramBot) -> Bot:
    """Deprecated thin wrapper retained for compatibility in tests/imports."""
    from services.telegram.bot_factory import build_personal_bot

    return build_personal_bot(telegram_bot)


async def process_update(telegram_bot: TelegramBot, raw_update: dict) -> None:
    dispatcher = get_personal_dispatcher()
    bot = await get_personal_bot(telegram_bot)
    update_id = raw_update.get("update_id")
    update_type = next((key for key in raw_update.keys() if key != "update_id"), "unknown")

    try:
        update = Update.model_validate(raw_update)
        await dispatcher.feed_update(bot, update, telegram_bot=telegram_bot)
    except Exception:
        logger.exception(
            "personal bot update processing failed bot_id=%s specialist_id=%s update_id=%s",
            telegram_bot.bot_user_id,
            telegram_bot.specialist_id,
            update_id,
        )
        return

    logger.info(
        "personal bot update processed bot_id=%s specialist_id=%s update_id=%s update_type=%s",
        telegram_bot.bot_user_id,
        telegram_bot.specialist_id,
        update_id,
        update_type,
    )
