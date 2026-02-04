import asyncio
from aiogram import Bot, Dispatcher, types

# Токен пока оставим пустым для теста
TOKEN = "123:ABC" 

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    print("Бот готов к запуску (тестовый режим)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        pass