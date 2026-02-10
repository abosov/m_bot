import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject, Update
from sqlalchemy import select

from database import SpecialistProfile, TelegramBot, async_session_factory
from handlers.personal_bot import router as personal_router
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

            if profile is not None:
                data["owner_tg_user_id"] = profile["owner_tg_user_id"]
                data["public_name"] = profile["public_name"]
                if sender_id is not None and sender_id == profile["owner_tg_user_id"]:
                    data["actor"] = "specialist"

        return await handler(event, data)


def get_personal_dispatcher() -> Dispatcher:
    global _personal_dispatcher
    if _personal_dispatcher is None:
        dp = Dispatcher()
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
