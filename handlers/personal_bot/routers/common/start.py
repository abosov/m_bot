from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="personal_bot_common_start")

_SUPPORT_URL = "https://t.me/zumbot_support"


@router.message(Command("start"))
async def personal_start(
    message: Message,
    actor: str,
    public_name: str | None,
) -> None:
    if actor == "specialist":
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
