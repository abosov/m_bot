import logging

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from config import SUPPORT_TG_URL
from handlers.personal_bot.routers.specialist.owner_panel import send_owner_panel

router = Router(name="personal_bot_common_start")
logger = logging.getLogger(__name__)


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


@router.message(CommandStart())
async def personal_start(
    message: Message,
    command: CommandObject,
    actor: str,
    specialist_id,
    public_name: str | None,
    owner_tg_user_id: int | None,
) -> None:
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

        if command.args and command.args != "owner_panel":
            await message.answer("ℹ️ Неизвестный старт-параметр. Открываю панель специалиста.")

        try:
            await send_owner_panel(
                message=message,
                specialist_id=specialist_id,
                public_name=resolved_public_name,
                owner_tg_user_id=resolved_owner_tg_user_id,
            )
        except Exception:
            logger.exception(
                "personal_start: send_owner_panel failed, specialist_id=%s, tg_user_id=%s",
                specialist_id,
                resolved_owner_tg_user_id,
            )
            await message.answer(
                "⚠️ Панель специалиста временно недоступна. "
                f"Попробуйте позже или обратитесь в поддержку: {SUPPORT_TG_URL}"
            )

        await message.answer(
            "Доступно сейчас:\n"
            "• /status — состояние интеграций\n"
            "• /help — список команд\n\n"
            f"Поддержка: {SUPPORT_TG_URL}"
        )
        return

    try:
        await message.answer("👋 Запись скоро будет доступна. Пока это клиентская заглушка MVP.")
    except Exception:
        logger.exception("personal_start: failed to send client placeholder")
