import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold

# Токен лучше хранить в переменных окружения
TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

router = Router()

def get_echo_text(text: str) -> str:
    """Простая логика формирования ответа (для теста)"""
    return f"Вы написали: {text}"

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {hbold(message.from_user.full_name)}! Я эхо-бот.")

@router.message()
async def echo_handler(message: types.Message) -> None:
    try:
        # Используем логическую функцию
        response = get_echo_text(message.text)
        await message.answer(response)
    except TypeError:
        await message.answer("Я понимаю только текст!")

async def main() -> None:
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())