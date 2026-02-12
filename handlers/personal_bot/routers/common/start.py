from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from config import SUPPORT_TG_URL
from handlers.personal_bot.routers.specialist.owner_panel import send_owner_panel

router = Router(name="personal_bot_common_start")


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
        if command.args and command.args != "owner_panel":
            await message.answer("ℹ️ Неизвестный старт-параметр. Открываю панель специалиста.")

        await send_owner_panel(
            message=message,
            specialist_id=specialist_id,
            public_name=public_name,
            owner_tg_user_id=owner_tg_user_id,
        )
        await message.answer(
            "Доступно сейчас:\n"
            "• /status — состояние интеграций\n"
            "• /help — список команд\n\n"
            f"Поддержка: {SUPPORT_TG_URL}"
        )
        return

    await message.answer("👋 Запись скоро будет доступна. Пока это клиентская заглушка MVP.")
