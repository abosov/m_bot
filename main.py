# src/main.py

import asyncio
import os
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Импортируем роутер онбординга
from handlers.master_onboarding import router as master_onboarding_router
from database import init_db

# Импортируем Middleware
from logging_middleware import StructLoggingMiddleware

# Импортируем веб-сервер
from web_server import app as fastapi_app

load_dotenv()

# Настройка логирования (базовый уровень stdout)
logging.basicConfig(level=logging.INFO)

async def start_web_server():
    """Запуск uvicorn в асинхронном режиме"""
    config = uvicorn.Config(
        app=fastapi_app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def start_bot():
    """Запуск Telegram бота"""
    # Инициализация БД
    await init_db()
    
    token = os.getenv("MASTER_BOT_TOKEN")
    if not token:
        raise ValueError("MASTER_BOT_TOKEN not set")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    dp.update.outer_middleware(StructLoggingMiddleware())
    dp.include_router(master_onboarding_router)

    # Удаляем вебхук для Master Bot (для режима polling)
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("🚀 Master Bot запущен в режиме Polling...")
    await dp.start_polling(bot)

async def main():
    # Запускаем параллельно и бота, и веб-сервер
    await asyncio.gather(
        start_bot(),
        start_web_server()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Application stopped")