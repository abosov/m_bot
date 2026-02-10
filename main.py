# src/main.py

import asyncio
import os
import logging
import signal
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import config

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
from services.heartbeat import heartbeat_task

async def start_web_server():
    """Запуск uvicorn в асинхронном режиме"""

    # systemd socket activation: если есть LISTEN_FDS=1 и PID совпал — слушаем fd=3
    listen_fds = os.getenv("LISTEN_FDS")
    listen_pid = os.getenv("LISTEN_PID")
    use_fd3 = (listen_fds == "1" and listen_pid and int(listen_pid) == os.getpid())

    if use_fd3:
        server_config = uvicorn.Config(
            app=fastapi_app,
            fd=3,
            log_level="info",
        )
        logger.info("🌍 Web server starting via systemd socket (fd=3)...")
    else:
        server_config = uvicorn.Config(
            app=fastapi_app,
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            log_level="info",
        )
        logger.info("🌍 Web server starting on %s:%s...", config.WEB_HOST, config.WEB_PORT)

    server = uvicorn.Server(server_config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        logger.info("🌍 Web server stopping...")
        server.should_exit = True
        await server.shutdown()
        raise

async def start_bot():
    """Запуск Telegram бота"""
    # Инициализация БД
    await init_db()
    
    token = config.MASTER_BOT_TOKEN
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
        await dp.start_polling(bot, handle_signals=False)
    except asyncio.CancelledError:
        logger.info("🤖 Bot polling cancelled...")
    finally:
        await bot.session.close()
        logger.info("🤖 Bot session closed.")

async def main():
    """Точка входа: запускает бота и веб-сервер параллельно"""
    stop_event = asyncio.Event()
    logger.info(
        "🚀 Startup config APP_ENV=%s ENABLE_READYZ=%s WEB_HOST=%s WEB_PORT=%s",
        config.APP_ENV,
        config.ENABLE_READYZ,
        config.WEB_HOST,
        config.WEB_PORT,
    )

    def request_shutdown():
        if not stop_event.is_set():
            logger.info("🛑 Shutdown signal received, stopping...")
            stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_shutdown)
        except NotImplementedError:
            signal.signal(sig, lambda *_: request_shutdown())

    # Создаем задачи
    bot_task = asyncio.create_task(start_bot())
    server_task = asyncio.create_task(start_web_server())
    heartbeat = asyncio.create_task(heartbeat_task())
    shutdown_task = asyncio.create_task(stop_event.wait())
    
    # Ожидаем завершения (или отмены)
    try:
        done, _pending = await asyncio.wait(
            {bot_task, server_task, heartbeat, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if shutdown_task not in done:
            for task in done:
                if task.exception():
                    raise task.exception()
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
        if not heartbeat.done():
            heartbeat.cancel()
        if not shutdown_task.done():
            shutdown_task.cancel()
        
        # Даем время на cleanup
        await asyncio.gather(
            bot_task,
            server_task,
            heartbeat,
            shutdown_task,
            return_exceptions=True,
        )

if __name__ == "__main__":
    try:
        config.validate_config()
        # Запускаем основной цикл
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Application stopped manually.")
