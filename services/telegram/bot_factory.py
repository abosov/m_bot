import logging
import time
import asyncio
from aiohttp import ClientTimeout
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from database import TelegramBot
from services.crypto import decrypt_token

logger = logging.getLogger(__name__)

_PERSONAL_BOT_CACHE_TTL_SEC = 90.0
_personal_bot_cache: dict[int, tuple[float, Bot]] = {}
_personal_bot_cache_lock = asyncio.Lock()


def _build_session() -> AiohttpSession:
    timeout = ClientTimeout(total=15.0, connect=5.0, sock_read=10.0)
    return AiohttpSession(timeout=timeout)


def build_personal_bot(telegram_bot: TelegramBot) -> Bot:
    token = decrypt_token(telegram_bot.bot_token_encrypted)
    return Bot(
        token=token,
        session=_build_session(),
        default=DefaultBotProperties(),
    )


async def _close_bot(bot: Bot) -> None:
    try:
        await bot.session.close()
    except Exception:
        logger.exception("failed to close cached personal bot session")


async def _cleanup_expired(now: float) -> None:
    bots_to_close: list[Bot] = []
    async with _personal_bot_cache_lock:
        expired_ids = [bot_id for bot_id, (expires_at, _) in _personal_bot_cache.items() if expires_at <= now]
        for bot_id in expired_ids:
            _, bot = _personal_bot_cache.pop(bot_id)
            bots_to_close.append(bot)

    for bot in bots_to_close:
        await _close_bot(bot)


async def get_personal_bot(telegram_bot: TelegramBot) -> Bot:
    now = time.monotonic()
    await _cleanup_expired(now)

    bot_id = telegram_bot.bot_user_id
    async with _personal_bot_cache_lock:
        cached = _personal_bot_cache.get(bot_id)
        if cached is not None:
            _, bot = cached
            _personal_bot_cache[bot_id] = (now + _PERSONAL_BOT_CACHE_TTL_SEC, bot)
            return bot

        bot = build_personal_bot(telegram_bot)
        _personal_bot_cache[bot_id] = (now + _PERSONAL_BOT_CACHE_TTL_SEC, bot)
        return bot


async def close_personal_bot_cache() -> None:
    bots_to_close: list[Bot] = []
    async with _personal_bot_cache_lock:
        bot_ids = list(_personal_bot_cache.keys())
        for bot_id in bot_ids:
            _, bot = _personal_bot_cache.pop(bot_id)
            bots_to_close.append(bot)

    for bot in bots_to_close:
        await _close_bot(bot)
