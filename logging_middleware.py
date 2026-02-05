import time
import traceback
import uuid
from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from sqlalchemy import select

from database import async_session_factory, MessageLog, LogDirection, TelegramBot

# Простой кэш для сопоставления bot_id -> specialist_id, чтобы не нагружать БД каждым запросом
# В продакшене лучше использовать Redis или TTLCache
_bot_specialist_cache: Dict[int, Optional[uuid.UUID]] = {}

async def _get_specialist_id(bot_id: int) -> Optional[uuid.UUID]:
    """Получает ID специалиста по ID бота с кэшированием."""
    if bot_id in _bot_specialist_cache:
        return _bot_specialist_cache[bot_id]

    async with async_session_factory() as session:
        stmt = select(TelegramBot.specialist_id).where(TelegramBot.bot_user_id == bot_id)
        result = await session.execute(stmt)
        specialist_id = result.scalar_one_or_none()
        
        # Кэшируем результат (даже если None, например для master_bot)
        _bot_specialist_cache[bot_id] = specialist_id
        return specialist_id

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
        tg_user_id = 0
        message_type = "unknown"
        content = None
        handler_name = None

        # Извлечение данных из события
        if isinstance(event, Update):
            # Middleware aiogram часто работает с Update, но outer_middleware может получать конкретные типы
            # Если это Update, пытаемся достать вложенный объект
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
            message_type = "callback_query"
            content = actual_event.data

        # Попытка определить имя хендлера (доступно только для inner middleware, 
        # но в outer handler может быть еще не определен, поэтому оставим пустым или попробуем)
        if "handler" in data:
             # Это работает чаще в inner middleware
             handler_obj = data.get("handler")
             if hasattr(handler_obj, "callback"):
                 handler_name = handler_obj.callback.__name__

        # Получаем specialist_id
        try:
            specialist_id = await _get_specialist_id(bot_id)
        except Exception:
            # Не даем ошибке логирования сломать обработку
            pass

        # Выполнение хендлера и перехват ошибок
        is_error = False
        error_details = None
        
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            is_error = True
            error_details = traceback.format_exc()
            raise e  # Пробрасываем ошибку дальше, чтобы aiogram (или другие middleware) могли её обработать
        finally:
            # Запись лога в БД (выполняется всегда, даже при ошибке)
            processing_time = time.time() - start_time
            
            try:
                # Если tg_user_id не определен (например, системное событие), логируем 0 или пропускаем
                if tg_user_id:
                    async with async_session_factory() as session:
                        log_entry = MessageLog(
                            specialist_id=specialist_id,
                            bot_id=bot_id,
                            tg_user_id=tg_user_id,
                            direction=LogDirection.IN,
                            message_type=message_type,
                            content=content,
                            is_error=is_error,
                            error_details=error_details,
                            processing_time=processing_time,
                            handler_name=handler_name
                        )
                        session.add(log_entry)
                        await session.commit()
            except Exception as log_exc:
                # Критично: ошибка логирования не должна валить бота, выводим в stderr
                print(f"FAILED TO WRITE LOG: {log_exc}")


async def log_outbound_message(
    bot: Bot,
    tg_user_id: int,
    content: str,
    message_type: str = "text"
):
    """
    Вспомогательная функция для логирования исходящих сообщений.
    Должна вызываться вручную после отправки сообщения (или через декоратор метода bot.send_message).
    """
    try:
        bot_id = bot.id
        specialist_id = await _get_specialist_id(bot_id)
        
        async with async_session_factory() as session:
            log_entry = MessageLog(
                specialist_id=specialist_id,
                bot_id=bot_id,
                tg_user_id=tg_user_id,
                direction=LogDirection.OUT,
                message_type=message_type,
                content=content,
                is_error=False,
                processing_time=0.0 # Для исходящих время обработки менее релевантно в этом контексте
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        print(f"FAILED TO WRITE OUTBOUND LOG: {e}")