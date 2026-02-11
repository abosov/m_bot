from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from handlers.personal_bot.routers.specialist.owner_panel import send_owner_panel

router = Router(name="personal_bot_common_start")

_SUPPORT_URL = "https://t.me/zumbot_support"


@router.message(CommandStart())
async def personal_start(
    message: Message,
    command: CommandObject,
    actor: str,
    specialist_id,
    public_name: str | None,
) -> None:
    if actor == "specialist":
        if command.args == "owner_panel":
            await send_owner_panel(message=message, specialist_id=specialist_id, public_name=public_name)
            return

        display_name = public_name or "специалист"
        text = (
            f"👋 Панель специалиста, {display_name}.\n\n"
            "Доступно сейчас:\n"
            "• /status — состояние интеграций\n"
            "• /help — список команд\n\n"
            f"Поддержка: {_SUPPORT_URL}"
        )
        await message.answer(text)
        return

    await message.answer("👋 Запись скоро будет доступна. Пока это клиентская заглушка MVP.")
