# src/main.py

import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Импортируем роутер онбординга
from handlers.master_onboarding import router as master_onboarding_router
from database import init_db

# Импортируем Middleware
from logging_middleware import StructLoggingMiddleware

load_dotenv()

# Настройка логирования (базовый уровень stdout)
logging.basicConfig(level=logging.INFO)

async def main():
    # Инициализация БД (создание таблиц для MVP)
    await init_db()
    
    # Master Bot Token
    token = os.getenv("MASTER_BOT_TOKEN")
    if not token:
        raise ValueError("MASTER_BOT_TOKEN not set")

    # Инициализация бота и диспетчера
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    # --- Подключение Middleware ---
    # outer_middleware срабатывает ДО фильтров, что позволяет логировать все входящие апдейты
    dp.update.outer_middleware(StructLoggingMiddleware())

    # Регистрируем роутеры
    dp.include_router(master_onboarding_router)

    # Удаляем вебхук для Master Bot и запускаем поллинг (для dev-режима Master Bot)
    # В проде для Master Bot тоже будет вебхук, но для тестов поллинг удобнее
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("🚀 Master Bot запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")