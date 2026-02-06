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
    SpecialistCalendar,
)
from services.crypto import encrypt_token
# Импорт логирования исходящих сообщений
from logging_middleware import log_outbound_message

router = Router()

# --- FSM States ---
class OnboardingStates(StatesGroup):
    waiting_for_public_name = State()
    waiting_for_bot_token = State()

# --- Constants ---
BASE_URL = os.getenv("BASE_URL", "https://api.example.com")

def _get_handle(user: types.User) -> str:
    """Helper to get user handle for logs"""
    if user.username:
        return f"@{user.username}"
    parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(parts) if parts else str(user.id)


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
    
    user_handle = _get_handle(message.from_user)
    current_state = await state.get_state()

    async with async_session_factory() as session:
        # Проверяем, есть ли такой specialist_auth_telegram
        stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        auth_entry = result.scalar_one_or_none()
        
        specialist_name_for_log = None # Имя пока неизвестно или берем из профиля если есть

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
            
            text_out = (
                "Добро пожаловать в платформу записи клиентов!\n"
                "Давайте настроим вашего личного бота.\n\n"
                "Нажмите кнопку ниже, чтобы начать."
            )
            await message.answer(
                text_out,
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[[types.KeyboardButton(text="Стать специалистом")]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            await log_outbound_message(
                bot=message.bot,
                tg_user_id=tg_user_id,
                content=text_out,
                fsm_state=current_state,
                user_handle=user_handle
            )

        else:
            # Специалист уже есть, проверяем статус
            spec_stmt = select(Specialist).where(Specialist.specialist_id == auth_entry.specialist_id)
            spec_result = await session.execute(spec_stmt)
            specialist = spec_result.scalar_one()
            
            # Попробуем подгрузить имя для логов, если есть профиль
            prof_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == auth_entry.specialist_id)
            prof_res = await session.execute(prof_stmt)
            prof = prof_res.scalar_one_or_none()
            if prof:
                specialist_name_for_log = prof.public_name

            if specialist.status == SpecialistStatus.active:
                text_out = "Вы уже зарегистрированы и ваш бот активен!"
                await message.answer(text_out)
                await log_outbound_message(
                    bot=message.bot,
                    tg_user_id=tg_user_id,
                    content=text_out,
                    fsm_state=current_state,
                    user_handle=user_handle,
                    specialist_name=specialist_name_for_log
                )
            else:
                text_out = "Вы в процессе регистрации. Нажмите кнопку, чтобы продолжить."
                await message.answer(
                    text_out,
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[[types.KeyboardButton(text="Стать специалистом")]],
                        resize_keyboard=True
                    )
                )
                await log_outbound_message(
                    bot=message.bot,
                    tg_user_id=tg_user_id,
                    content=text_out,
                    fsm_state=current_state,
                    user_handle=user_handle,
                    specialist_name=specialist_name_for_log
                )


@router.message(F.text == "Стать специалистом")
async def start_flow(message: types.Message, state: FSMContext):
    """
    Переход к вводу публичного имени.
    """
    await state.set_state(OnboardingStates.waiting_for_public_name)
    
    user_handle = _get_handle(message.from_user)
    # Состояние уже изменилось, получаем новое
    new_state = await state.get_state()
    
    text_out = (
        "Шаг 1 из 3. Введите ваше публичное имя.\n"
        "Так вы будете отображаться клиентам (например: «Психолог Анна» или «Иван Иванов»)."
    )
    await message.answer(
        text_out,
        reply_markup=types.ReplyKeyboardRemove()
    )
    await log_outbound_message(
        bot=message.bot,
        tg_user_id=message.from_user.id,
        content=text_out,
        fsm_state=new_state,
        user_handle=user_handle
    )


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    """
    Шаг 2: Сохранение имени и запрос токена.
    """
    public_name = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    current_state = await state.get_state()

    async with async_session_factory() as session:
        # Находим специалиста
        stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        auth_entry = result.scalar_one()
        
        # Создаем или обновляем профиль
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
                specialist_timezone="UTC",
            )
            session.add(profile)
        else:
            profile.public_name = public_name
            profile.owner_tg_user_id = tg_user_id

        await session.commit()

    await state.set_state(OnboardingStates.waiting_for_bot_token)
    new_state = await state.get_state()
    
    text_out = (
        "Отлично! Шаг 2 из 3.\n\n"
        "Теперь создайте своего бота через @BotFather:\n"
        "1. Напишите ему /newbot\n"
        "2. Укажите имя и username бота\n"
        "3. Скопируйте полученный **API Token** и пришлите его сюда."
    )
    await message.answer(text_out)
    await log_outbound_message(
        bot=message.bot,
        tg_user_id=tg_user_id,
        content=text_out,
        fsm_state=new_state,
        user_handle=user_handle,
        specialist_name=public_name # Мы только что его узнали
    )


@router.message(OnboardingStates.waiting_for_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    """
    Шаг 3: Валидация токена, установка вебхука, сохранение.
    """
    raw_token = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    current_state = await state.get_state()
    
    # Имя можно было бы достать из БД, но для простоты здесь можем передать None,
    # так как Middleware попытается найти по specialist_id (который еще не привязан к этому temp_bot)
    # Но поскольку мы в мастере, то имя мы можем знать только через БД.
    # Для MVP оставим None или можно сделать доп запрос, но это перегрузит хендлер.

    # 1. Валидация токена через Telegram API
    temp_bot = Bot(token=raw_token)
    try:
        bot_info = await temp_bot.get_me()
    except Exception as e:
        await session.close() if 'session' in locals() else None # cleanup
        text_out = (
            f"❌ Неверный токен или ошибка API Telegram.\n"
            f"Проверьте токен и попробуйте снова.\nДетали: {e}"
        )
        await message.answer(text_out)
        await log_outbound_message(
            bot=message.bot, 
            tg_user_id=tg_user_id, 
            content=text_out,
            fsm_state=current_state,
            user_handle=user_handle
        )
        return
    finally:
        await temp_bot.session.close()

    # 2. Генерация секретов и URL
    webhook_secret = secrets.token_urlsafe(32)
    webhook_path = f"/tg/webhook/{bot_info.id}/{webhook_secret}"
    webhook_url = f"{BASE_URL}{webhook_path}"

    # 3. Установка вебхука
    temp_bot_webhook = Bot(token=raw_token)
    try:
        await temp_bot_webhook.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        text_out = (
            f"❌ Не удалось установить Webhook.\n"
            f"Убедитесь, что URL {BASE_URL} доступен из интернета (SSL обязателен).\n"
            f"Ошибка: {e}"
        )
        await message.answer(text_out)
        await log_outbound_message(
            bot=message.bot,
            tg_user_id=tg_user_id,
            content=text_out,
            fsm_state=current_state,
            user_handle=user_handle
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
        
        check_bot = select(TelegramBot).where(TelegramBot.bot_user_id == bot_info.id)
        if (await session.execute(check_bot)).scalar_one_or_none():
            text_out = "Этот бот уже зарегистрирован в системе."
            await message.answer(text_out)
            await log_outbound_message(
                bot=message.bot,
                tg_user_id=tg_user_id,
                content=text_out,
                fsm_state=current_state,
                user_handle=user_handle
            )
            return

        session.add(new_bot)
        await session.commit()

    # Сбрасываем состояние
    await state.clear()
    
    # New state is None
    new_state = None

    text_out = (
        f"✅ Бот **@{bot_info.username}** успешно подключен!\n\n"
        f"Следующий шаг: **Подключение Google Calendar**.\n"
        f"(Эта часть будет реализована в следующих задачах).\n\n"
        f"Пока что ваш статус регистрации: `onboarding`."
    )
    await message.answer(text_out)
    await log_outbound_message(
        bot=message.bot,
        tg_user_id=tg_user_id,
        content=text_out,
        fsm_state=new_state,
        user_handle=user_handle
    )