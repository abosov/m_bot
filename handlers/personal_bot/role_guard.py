import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)

_DENIED_TEXT = "ℹ️ Команда доступна только специалисту."


class SpecialistRoleGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if data.get("actor") == "specialist":
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(_DENIED_TEXT)
        elif isinstance(event, CallbackQuery):
            await event.answer("Команда доступна только специалисту", show_alert=True)

        logger.info(
            "specialist command blocked for non-specialist actor=%s user_id=%s",
            data.get("actor"),
            _extract_user_id(event),
        )
        return None


def _extract_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user.id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None
