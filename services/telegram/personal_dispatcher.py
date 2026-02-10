import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from database import TelegramBot
from handlers.personal_bot import router as personal_router
from services.crypto import decrypt_token

logger = logging.getLogger(__name__)

_personal_dispatcher: Dispatcher | None = None


def get_personal_dispatcher() -> Dispatcher:
    global _personal_dispatcher
    if _personal_dispatcher is None:
        dp = Dispatcher()
        dp.include_router(personal_router)
        _personal_dispatcher = dp
    return _personal_dispatcher


def build_bot_from_db(telegram_bot: TelegramBot) -> Bot:
    token = decrypt_token(telegram_bot.bot_token_encrypted)
    return Bot(token=token)


async def process_update(telegram_bot: TelegramBot, raw_update: dict) -> None:
    dispatcher = get_personal_dispatcher()
    bot = build_bot_from_db(telegram_bot)
    try:
        update = Update.model_validate(raw_update)
        await dispatcher.feed_update(bot, update)
    finally:
        await bot.session.close()

    update_id = raw_update.get("update_id")
    update_type = next((key for key in raw_update.keys() if key != "update_id"), "unknown")
    logger.info(
        "personal bot update processed bot_id=%s specialist_id=%s update_id=%s update_type=%s",
        telegram_bot.bot_user_id,
        telegram_bot.specialist_id,
        update_id,
        update_type,
    )
