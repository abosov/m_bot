import time
import traceback
import uuid
from typing import Callable, Dict, Any, Awaitable, Optional, Tuple

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, Update, User
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import async_session_factory, MessageLog, LogDirection, TelegramBot, SpecialistProfile

# Структура кэша: bot_id -> {'id': uuid, 'name': str, 'bot_username': str}
# В продакшене лучше использовать Redis или TTLCache
_bot_info_cache: Dict[int, Optional[Dict[str, Any]]] = {}

async def _get_specialist_info(bot_id: int) -> Optional[Dict[str, Any]]:
    """Получает ID специалиста, имя и username бота по ID бота с кэшированием."""
    if bot_id in _bot_info_cache:
        return _bot_info_cache[bot_id]

    async with async_session_factory() as session:
        # Джойним таблицу ботов и профиль специалиста
        stmt = (
            select(TelegramBot, SpecialistProfile.public_name)
            .outerjoin(SpecialistProfile, TelegramBot.specialist_id == SpecialistProfile.specialist_id)
            .where(TelegramBot.bot_user_id == bot_id)
        )
        result = await session.execute(stmt)
        row = result.first()
        
        info = None
        if row:
            tg_bot_entry, public_name = row
            info = {
                'id': tg_bot_entry.specialist_id,
                'name': public_name,
                'bot_username': tg_bot_entry.bot_username
            }
        
        # Кэшируем результат (даже если None, например для неавторизованных ботов)
        _bot_info_cache[bot_id] = info
        return info

def _get_user_handle(user: User) -> str:
    """Формирует читаемый handle пользователя (@username или First Last)."""
    if user.username:
        return f"@{user.username}"
    name_parts = [p for p in [user.first_name, user.last_name] if p]
    return " ".join(name_parts) if name_parts else str(user.id)

class StructLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        start_time = time.time()
        bot: Bot = data.get("bot")
        
        # Определяем основные параметры для лога
        bot_id = bot.id if bot else 0
        specialist_id = None
        specialist_name = None
        bot_username = None
        
        tg_user_id = 0
        user_handle = None
        
        message_type = "unknown"
        content = None
        handler_name = None
        fsm_state = None

        # --- Извлечение FSM State ---
        state_ctx: Optional[FSMContext] = data.get("state")
        if state_ctx:
            fsm_state = await state_ctx.get_state()

        # --- Извлечение данных из события ---
        if isinstance(event, Update):
            if event.message:
                actual_event = event.message
                message_type = "message"
            elif event.callback_query:
                actual_event = event.callback_query
                message_type = "callback_query"
            else:
                actual_event = event
                message_type = "other_update"
        else:
            actual_event = event

        if isinstance(actual_event, Message):
            tg_user_id = actual_event.from_user.id
            user_handle = _get_user_handle(actual_event.from_user)
            message_type = "message"
            
            if actual_event.text:
                content = actual_event.text
            elif actual_event.caption:
                content = f"[Caption] {actual_event.caption}"
            elif actual_event.photo:
                content = "[Photo]"
            elif actual_event.document:
                content = "[Document]"
            else:
                content = "[Other Content]"
                
        elif isinstance(actual_event, CallbackQuery):
            tg_user_id = actual_event.from_user.id
            user_handle = _get_user_handle(actual_event.from_user)
            message_type = "callback_query"
            content = actual_event.data

        # --- Определение Handler Name ---
        if "handler" in data:
             handler_obj = data.get("handler")
             if hasattr(handler_obj, "callback"):
                 handler_name = handler_obj.callback.__name__

        # --- Получение инфо о специалисте ---
        try:
            spec_info = await _get_specialist_info(bot_id)
            if spec_info:
                specialist_id = spec_info['id']
                specialist_name = spec_info['name']
                bot_username = spec_info['bot_username']
            else:
                # Если в БД нет (например, master_bot без привязки к специалисту)
                # Попробуем взять username у самого бота (обычно есть в кэше aiogram)
                me = await bot.get_me()
                bot_username = me.username
                
        except Exception:
            pass

        # --- Выполнение хендлера и перехват ошибок ---
        is_error = False
        error_details = None
        
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            is_error = True
            error_details = traceback.format_exc()
            raise e
        finally:
            # --- Запись лога ---
            processing_time = time.time() - start_time
            
            try:
                if tg_user_id:
                    async with async_session_factory() as session:
                        log_entry = MessageLog(
                            specialist_id=specialist_id,
                            specialist_name=specialist_name,
                            bot_id=bot_id,
                            bot_username=bot_username,
                            tg_user_id=tg_user_id,
                            user_handle=user_handle,
                            direction=LogDirection.IN,
                            message_type=message_type,
                            content=content,
                            fsm_state=fsm_state,
                            handler_name=handler_name,
                            is_error=is_error,
                            error_details=error_details,
                            processing_time=processing_time
                        )
                        session.add(log_entry)
                        await session.commit()
            except Exception as log_exc:
                print(f"FAILED TO WRITE LOG: {log_exc}")


async def log_outbound_message(
    bot: Bot,
    tg_user_id: int,
    content: str,
    message_type: str = "text",
    fsm_state: Optional[str] = None,
    specialist_name: Optional[str] = None,
    user_handle: Optional[str] = None
):
    """
    Вспомогательная функция для логирования исходящих сообщений.
    Теперь принимает контекстные аргументы для V2 логов.
    """
    try:
        bot_id = bot.id
        
        # Пытаемся достать данные из кэша
        spec_info = await _get_specialist_info(bot_id)
        
        specialist_id = None
        bot_username = None
        cached_spec_name = None

        if spec_info:
            specialist_id = spec_info['id']
            cached_spec_name = spec_info['name']
            bot_username = spec_info['bot_username']
        else:
            # Fallback для master_bot
            me = await bot.get_me()
            bot_username = me.username

        # Используем переданное имя или из кэша
        final_specialist_name = specialist_name or cached_spec_name

        async with async_session_factory() as session:
            log_entry = MessageLog(
                specialist_id=specialist_id,
                specialist_name=final_specialist_name,
                bot_id=bot_id,
                bot_username=bot_username,
                tg_user_id=tg_user_id,
                user_handle=user_handle,
                direction=LogDirection.OUT,
                message_type=message_type,
                content=content,
                fsm_state=fsm_state,
                is_error=False,
                processing_time=0.0
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        print(f"FAILED TO WRITE OUTBOUND LOG: {e}")