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
# Импорт сервиса OAuth
from services.google_oauth import get_auth_url

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

# ... (Код handlers cmd_start, start_flow, process_public_name остается без изменений) ...
# ... (Я приведу только process_public_name, чтобы не дублировать огромный кусок,
#      но в финальном файле нужно оставить все предыдущие хендлеры) ...
# Для полноты ответа, я приведу полный код файла с изменениями в process_bot_token

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # (Код без изменений из предыдущего шага)
    tg_user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    user_handle = _get_handle(message.from_user)
    current_state = await state.get_state()

    async with async_session_factory() as session:
        stmt = select(SpecialistAuthTelegram).where(
            SpecialistAuthTelegram.tg_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        auth_entry = result.scalar_one_or_none()
        
        specialist_name_for_log = None 

        if not auth_entry:
            new_specialist = Specialist(status=SpecialistStatus.onboarding)
            session.add(new_specialist)
            await session.flush() 

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
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle)

        else:
            spec_stmt = select(Specialist).where(Specialist.specialist_id == auth_entry.specialist_id)
            spec_result = await session.execute(spec_stmt)
            specialist = spec_result.scalar_one()
            
            prof_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == auth_entry.specialist_id)
            prof_res = await session.execute(prof_stmt)
            prof = prof_res.scalar_one_or_none()
            if prof:
                specialist_name_for_log = prof.public_name

            if specialist.status == SpecialistStatus.active:
                text_out = "Вы уже зарегистрированы и ваш бот активен!"
                await message.answer(text_out)
                await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle, specialist_name=specialist_name_for_log)
            else:
                text_out = "Вы в процессе регистрации. Нажмите кнопку, чтобы продолжить."
                await message.answer(
                    text_out,
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[[types.KeyboardButton(text="Стать специалистом")]],
                        resize_keyboard=True
                    )
                )
                await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle, specialist_name=specialist_name_for_log)


@router.message(F.text == "Стать специалистом")
async def start_flow(message: types.Message, state: FSMContext):
    await state.set_state(OnboardingStates.waiting_for_public_name)
    user_handle = _get_handle(message.from_user)
    new_state = await state.get_state()
    text_out = "Шаг 1 из 3. Введите ваше публичное имя."
    await message.answer(text_out, reply_markup=types.ReplyKeyboardRemove())
    await log_outbound_message(message.bot, message.from_user.id, text_out, fsm_state=new_state, user_handle=user_handle)


@router.message(OnboardingStates.waiting_for_public_name)
async def process_public_name(message: types.Message, state: FSMContext):
    public_name = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)

    async with async_session_factory() as session:
        stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
        result = await session.execute(stmt)
        auth_entry = result.scalar_one()
        
        profile_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == auth_entry.specialist_id)
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
    text_out = "Отлично! Шаг 2 из 3.\n\nТеперь создайте бота через @BotFather и пришлите API Token."
    await message.answer(text_out)
    await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=new_state, user_handle=user_handle, specialist_name=public_name)


@router.message(OnboardingStates.waiting_for_bot_token)
async def process_bot_token(message: types.Message, state: FSMContext):
    """
    Шаг 3: Валидация токена и (НОВОЕ) выдача ссылки на Google Auth.
    """
    raw_token = message.text.strip()
    tg_user_id = message.from_user.id
    user_handle = _get_handle(message.from_user)
    current_state = await state.get_state()
    
    # Пытаемся получить имя из БД
    async with async_session_factory() as session:
        auth_stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
        auth_res = await session.execute(auth_stmt)
        auth_entry = auth_res.scalar_one()
        
        prof_stmt = select(SpecialistProfile).where(SpecialistProfile.specialist_id == auth_entry.specialist_id)
        prof_res = await session.execute(prof_stmt)
        prof = prof_res.scalar_one_or_none()
        specialist_name = prof.public_name if prof else None
        specialist_id = auth_entry.specialist_id

    # 1. Валидация (упрощенно копируем из прошлой версии)
    temp_bot = Bot(token=raw_token)
    try:
        bot_info = await temp_bot.get_me()
    except Exception as e:
        await session.close() if 'session' in locals() else None 
        text_out = f"❌ Неверный токен. Детали: {e}"
        await message.answer(text_out)
        await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle)
        return
    finally:
        await temp_bot.session.close()

    # 2. Установка вебхука
    webhook_secret = secrets.token_urlsafe(32)
    webhook_path = f"/tg/webhook/{bot_info.id}/{webhook_secret}"
    webhook_url = f"{BASE_URL}{webhook_path}"

    temp_bot_webhook = Bot(token=raw_token)
    try:
        await temp_bot_webhook.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
    except Exception as e:
        text_out = f"❌ Ошибка вебхука: {e}"
        await message.answer(text_out)
        await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle)
        await temp_bot_webhook.session.close()
        return
    finally:
        await temp_bot_webhook.session.close()

    # 3. Сохранение в БД
    encrypted_token = encrypt_token(raw_token)
    
    async with async_session_factory() as session:
        new_bot = TelegramBot(
            specialist_id=specialist_id,
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
            text_out = "Этот бот уже зарегистрирован."
            await message.answer(text_out)
            await log_outbound_message(message.bot, tg_user_id, text_out, fsm_state=current_state, user_handle=user_handle)
            return

        session.add(new_bot)
        await session.commit()

    # Сбрасываем состояние
    await state.clear()
    
    # 4. (НОВОЕ) Генерация ссылки на Google Auth
    auth_url = get_auth_url(specialist_id)

    text_out = (
        f"✅ Бот **@{bot_info.username}** подключен!\n\n"
        f"Последний шаг: **Подключите Google Calendar**.\n"
        f"Это нужно, чтобы мы могли видеть вашу занятость и создавать встречи."
    )
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text="🔗 Подключить Google Календарь", url=auth_url)
        ]]
    )

    await message.answer(text_out, reply_markup=keyboard)
    await log_outbound_message(
        bot=message.bot,
        tg_user_id=tg_user_id,
        content=text_out + f" [Link: {auth_url}]", # Логируем факт отправки ссылки
        fsm_state=None,
        user_handle=user_handle,
        specialist_name=specialist_name
    )