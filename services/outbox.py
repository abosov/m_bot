from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import OutboxEvent, async_session_factory
from services.log_context import log_event

logger = logging.getLogger(__name__)

OutboxHandler = Callable[[AsyncSession, OutboxEvent], Awaitable[None]]
OUTBOX_EVENT_HANDLERS: dict[str, OutboxHandler] = {}
OUTBOX_POLL_INTERVAL_SEC = 5.0
_SENSITIVE_ERROR_TOKEN_PATTERN = re.compile(
    r"(?i)(access_token|refresh_token|webhook_secret)(\s*[=:]\s*)([^\s,;]+)"
)


def _format_outbox_error(exc: Exception) -> str:
    exception_class = exc.__class__.__name__
    message = str(exc).replace("\r", " ").replace("\n", " ")
    message = _SENSITIVE_ERROR_TOKEN_PATTERN.sub(r"\1\2[REDACTED]", message)
    message = " ".join(message.split())[:300]
    return f"{exception_class}: {message}" if message else exception_class


async def emit_domain_event(session, event_type: str, payload: dict) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, payload_json=payload)
    session.add(event)
    return event


async def _dispatch_outbox_event(session: AsyncSession, event: OutboxEvent) -> bool:
    handler = OUTBOX_EVENT_HANDLERS.get(event.event_type)
    if handler is None:
        log_event(
            logger,
            logging.INFO,
            event="outbox_event_handler_missing",
            outbox_event_id=event.id,
            event_type=event.event_type,
        )
        return False

    await handler(session, event)
    return True


async def process_outbox_events(limit: int = 50) -> int:
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.processed_at.is_(None))
                .order_by(OutboxEvent.created_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            events = result.scalars().all()

            for outbox_event in events:
                try:
                    was_dispatched = await _dispatch_outbox_event(session, outbox_event)
                    outbox_event.processed_at = datetime.now(timezone.utc)
                    outbox_event.error = None if was_dispatched else "handler_missing"
                except Exception as exc:
                    outbox_event.attempts += 1
                    outbox_event.error = _format_outbox_error(exc)
                    log_event(
                        logger,
                        logging.ERROR,
                        event="outbox_event_process_failed",
                        outbox_event_id=outbox_event.id,
                        event_type=outbox_event.event_type,
                        exception_class=exc.__class__.__name__,
                    )

            return len(events)


async def outbox_worker_task() -> None:
    logger.info("outbox_worker_task started")
    try:
        while True:
            try:
                await process_outbox_events()
            except Exception as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    event="outbox_worker_cycle_failed",
                    exception_class=exc.__class__.__name__,
                )
            await asyncio.sleep(OUTBOX_POLL_INTERVAL_SEC)
    except asyncio.CancelledError:
        logger.info("outbox_worker_task stopped")
        raise


from services.outbox_notifications import register_outbox_handlers

register_outbox_handlers(OUTBOX_EVENT_HANDLERS)
