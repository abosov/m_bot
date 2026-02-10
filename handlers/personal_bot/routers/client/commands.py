from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="personal_bot_client_commands")


@router.message(Command("help"))
async def personal_help_client(message: Message) -> None:
    await message.answer("ℹ️ Скоро здесь появится клиентский сценарий записи.")
