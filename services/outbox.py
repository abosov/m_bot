from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import select

from database import OutboxEvent, async_session_factory
from services.log_context import log_event

logger = logging.getLogger(__name__)

OutboxHandler = Callable[[OutboxEvent], Awaitable[None]]
OUTBOX_EVENT_HANDLERS: dict[str, OutboxHandler] = {}
OUTBOX_POLL_INTERVAL_SEC = 5.0


async def emit_domain_event(session, event_type: str, payload: dict) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, payload_json=payload)
    session.add(event)
    return event


async def _dispatch_outbox_event(event: OutboxEvent) -> None:
    handler = OUTBOX_EVENT_HANDLERS.get(event.event_type)
    if handler is None:
        log_event(
            logger,
            logging.INFO,
            event="outbox_event_handler_missing",
            outbox_event_id=event.id,
            event_type=event.event_type,
        )
        return

    await handler(event)


async def process_outbox_events(limit: int = 50) -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        events = result.scalars().all()

        for outbox_event in events:
            try:
                await _dispatch_outbox_event(outbox_event)
                outbox_event.processed_at = datetime.now(timezone.utc)
                outbox_event.error = None
            except Exception as exc:
                outbox_event.attempts += 1
                outbox_event.error = str(exc)
                log_event(
                    logger,
                    logging.ERROR,
                    event="outbox_event_process_failed",
                    outbox_event_id=outbox_event.id,
                    event_type=outbox_event.event_type,
                    exception_class=exc.__class__.__name__,
                )

        await session.commit()
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
