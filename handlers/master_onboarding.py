import uuid
import secrets
import os
from aiogram import Router, F, types, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Импорты из существующего database.py
from database import (
    async_session_factory,
    Specialist,
    SpecialistAuthTelegram,
    SpecialistProfile,
    SpecialistStatus,
    TelegramBot,
    TelegramBotStatus,
    SpecialistCalendar, # Placeholder if needed later
)
from services.crypto import encrypt_token

router = Router()

# --- FSM States ---
class OnboardingStates(StatesGroup):
    waiting_for_public_name = State()
    waiting_for_bot_token = State()

# --- Constants ---
BASE_URL = os.getenv("BASE_URL", "https://api.example.com")


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Шаг 1: Старт онбординга.
    Проверяет наличие специалиста, создает запись при отсутствии.
    """
    tg_user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    async with async_session_factory() as session:
        # Проверяем, есть ли такой specialist_auth_telegram
        stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        auth_entry = result.scalar_one_or_none()

        if not auth_entry:
            # Создаем нового специалиста и auth запись
            new_specialist = Specialist(status=SpecialistStatus.onboarding)
            session.add(new_specialist)
            await session.flush()  # Чтобы получить specialist_id

            new_auth = SpecialistAuthTelegram(
                specialist_id=new_specialist.specialist_id,
                tg_user_id=tg_user_id,
                tg_username=username,
                tg_first_name=first_name,
                tg_last_name=last_name
            )
            session.add(new_auth)
            await session.commit()
            
            await message.answer(
                "Добро пожаловать в платформу записи клиентов!\n"
                "Давайте настроим вашего личного бота.\n\n"
                "Нажмите кнопку ниже, чтобы начать.",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[[types.KeyboardButton(text="Стать специалистом")]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
        else:
            # Специалист уже есть, проверяем статус
            # Загружаем специалиста чтобы проверить статус
            spec_stmt = select(Specialist).where(Specialist.specialist_id == auth_entry.specialist_id)
            spec_result = await session.execute(spec_stmt)
            specialist = spec_result.scalar_one()

            if specialist.status == SpecialistStatus.active:
                await message.answer("Вы уже зарегистрированы и ваш бот активен!")
            else:
                await message.answer(
                    "Вы в процессе регистрации. Нажмите кнопку, чтобы продолжить.",
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[[types.KeyboardButton(text="Стать специалистом")]],
                        resize_keyboard=True
                    )
                )


@router.message(F.text == "Стать специалистом")
async def start_flow(message: types.Message, state: FSMContext):
    """
    Переход к вводу публичного имени.
    """
    await state.set_state(OnboardingStates.waiting_for_public_name)
    await message.answer(
        "Шаг 1 из 3. Введите ваше публичное имя.\n"
        "Так вы будете отображаться клиентам (например: «Психолог Анна» или «Иван Иванов»).",
        reply_markup=types.ReplyKeyboardRemove()
    )


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    """
    Шаг 2: Сохранение имени и запрос токена.
    """
    public_name = message.text.strip()
    tg_user_id = message.from_user.id

    async with async_session_factory() as session:
        # Находим специалиста
        stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        auth_entry = result.scalar_one() # Он точно есть после /start
        
        # Создаем или обновляем профиль
        # Проверяем, есть ли профиль
        profile_stmt = select(SpecialistProfile).where(
            SpecialistProfile.specialist_id == auth_entry.specialist_id
        )
        profile_res = await session.execute(profile_stmt)
        profile = profile_res.scalar_one_or_none()

        if not profile:
            profile = SpecialistProfile(
                specialist_id=auth_entry.specialist_id,
                public_name=public_name,
                owner_tg_user_id=tg_user_id,
                owner_tg_username=message.from_user.username,
                specialist_timezone="UTC", # Дефолт, обновится при подключении календаря
            )
            session.add(profile)
        else:
            profile.public_name = public_name
            profile.owner_tg_user_id = tg_user_id # Обновляем на всякий случай

        await session.commit()

    await state.set_state(OnboardingStates.waiting_for_bot_token)
    await message.answer(
        "Отлично! Шаг 2 из 3.\n\n"
        "Теперь создайте своего бота через @BotFather:\n"
        "1. Напишите ему /newbot\n"
        "2. Укажите имя и username бота\n"
        "3. Скопируйте полученный **API Token** и пришлите его сюда."
    )


@router.message(OnboardingStates.waiting_for_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    """
    Шаг 3: Валидация токена, установка вебхука, сохранение.
    """
    raw_token = message.text.strip()
    tg_user_id = message.from_user.id

    # 1. Валидация токена через Telegram API
    temp_bot = Bot(token=raw_token)
    try:
        bot_info = await temp_bot.get_me()
    except Exception as e:
        await session.close() if 'session' in locals() else None # cleanup
        await message.answer(
            f"❌ Неверный токен или ошибка API Telegram.\n"
            f"Проверьте токен и попробуйте снова.\nДетали: {e}"
        )
        return
    finally:
        await temp_bot.session.close()

    # 2. Генерация секретов и URL
    webhook_secret = secrets.token_urlsafe(32) # Секрет для URL
    # Формируем URL согласно telegram.md: /tg/webhook/{bot_id}/{secret}
    webhook_path = f"/tg/webhook/{bot_info.id}/{webhook_secret}"
    webhook_url = f"{BASE_URL}{webhook_path}"

    # 3. Установка вебхука
    # Мы используем тот же temp_bot для установки вебхука
    temp_bot_webhook = Bot(token=raw_token)
    try:
        # drop_pending_updates=True хорошая практика при новой привязке
        await temp_bot_webhook.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось установить Webhook.\n"
            f"Убедитесь, что URL {BASE_URL} доступен из интернета (SSL обязателен).\n"
            f"Ошибка: {e}"
        )
        await temp_bot_webhook.session.close()
        return
    finally:
        await temp_bot_webhook.session.close()

    # 4. Сохранение в БД
    encrypted_token = encrypt_token(raw_token)
    
    async with async_session_factory() as session:
        # Получаем ID специалиста
        auth_stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        auth_result = await session.execute(auth_stmt)
        auth_entry = auth_result.scalar_one()

        # Создаем запись TelegramBot
        new_bot = TelegramBot(
            specialist_id=auth_entry.specialist_id,
            bot_user_id=bot_info.id,
            bot_username=bot_info.username,
            bot_name=bot_info.first_name,
            bot_token_encrypted=encrypted_token,
            webhook_secret=webhook_secret,
            webhook_url=webhook_url,
            status=TelegramBotStatus.active
        )
        
        # Проверяем нет ли уже бота (UPSERT логика для MVP упрощена: удаляем старый если был или кидаем ошибку)
        # В MVP предполагаем, что это первый бот. Если user_id бота совпадет с существующим - упадет UniqueConstraint
        # Лучше проверить:
        check_bot = select(TelegramBot).where(TelegramBot.bot_user_id == bot_info.id)
        if (await session.execute(check_bot)).scalar_one_or_none():
            await message.answer("Этот бот уже зарегистрирован в системе.")
            return

        session.add(new_bot)
        await session.commit()

    # Сбрасываем состояние
    await state.clear()

    await message.answer(
        f"✅ Бот **@{bot_info.username}** успешно подключен!\n\n"
        f"Следующий шаг: **Подключение Google Calendar**.\n"
        f"(Эта часть будет реализована в следующих задачах).\n\n"
        f"Пока что ваш статус регистрации: `onboarding`."
    )