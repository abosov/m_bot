import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from database import init_db  # Импортируем нашу функцию из нового файла

# Настраиваем логирование, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO)

# Токен пока оставим тестовым
TOKEN = "123:ABC"

async def main():
    # 1. Инициализируем базу данных (создаем таблицы)
    logging.info("Инициализация базы данных...")
    await init_db()
    
    # 2. Запускаем бота
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    
    logging.info("Бот готов к запуску (тестовый режим)")
    
    # В асинхронном режиме используем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")