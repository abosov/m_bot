# src/main.py

import asyncio
import os
import logging
import uvicorn
from dotenv import load_dotenv

# 1. Сначала загружаем env, чтобы импорты не падали из-за отсутствия ключей
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Импортируем роутер онбординга
from handlers.master_onboarding import router as master_onboarding_router
from database import init_db

# Импортируем Middleware
from logging_middleware import StructLoggingMiddleware

# Импортируем веб-сервер
from web_server import app as fastapi_app

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_web_server():
    """Запуск uvicorn в асинхронном режиме"""
    config = uvicorn.Config(
        app=fastapi_app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    logger.info("🌍 Web server starting on port 8000...")
    try:
        await server.serve()
    except asyncio.CancelledError:
        logger.info("🌍 Web server stopping...")

async def start_bot():
    """Запуск Telegram бота"""
    # Инициализация БД
    await init_db()
    
    token = os.getenv("MASTER_BOT_TOKEN")
    if not token:
        raise ValueError("MASTER_BOT_TOKEN not set")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher()

    # Подключаем Middleware и Роутер
    dp.update.outer_middleware(StructLoggingMiddleware())
    dp.include_router(master_onboarding_router)

    # Удаляем вебхук для Master Bot (для режима polling в dev)
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🤖 Master Bot starting polling...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("🤖 Bot polling cancelled...")
    finally:
        await bot.session.close()
        logger.info("🤖 Bot session closed.")

async def main():
    """Точка входа: запускает бота и веб-сервер параллельно"""
    
    # Создаем задачи
    bot_task = asyncio.create_task(start_bot())
    server_task = asyncio.create_task(start_web_server())
    
    # Ожидаем завершения (или отмены)
    try:
        await asyncio.gather(bot_task, server_task)
    except asyncio.CancelledError:
        logger.info("Main tasks cancelled, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        # Корректное завершение при ошибке или отмене
        if not bot_task.done():
            bot_task.cancel()
        if not server_task.done():
            server_task.cancel()
        
        # Даем время на cleanup
        await asyncio.gather(bot_task, server_task, return_exceptions=True)

if __name__ == "__main__":
    try:
        # Запускаем основной цикл
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Application stopped manually.")