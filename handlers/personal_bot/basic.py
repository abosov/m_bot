from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="personal_bot_basic")


@router.message(CommandStart())
async def personal_start(message: Message) -> None:
    await message.answer("Бот подключен. Скоро здесь появится запись/вопросы.")
