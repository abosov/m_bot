#!/usr/bin/env python3
"""Diagnostic helper for reminder pipeline counters (no secrets)."""

from __future__ import annotations

import asyncio
from sqlalchemy import func, select

from database import AppointmentReminder, OutboxEvent, async_session_factory

REMINDER_EVENT_TYPES = (
    "appointment_client_reminder_24h",
    "appointment_client_reminder_2h",
    "appointment_client_confirmed",
    "appointment_client_contact_specialist",
)


async def main() -> None:
    async with async_session_factory() as session:
        pending_reminders = await session.scalar(
            select(func.count()).select_from(AppointmentReminder).where(AppointmentReminder.sent_at_utc.is_(None))
        )
        pending_outbox = await session.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .where(OutboxEvent.event_type.in_(REMINDER_EVENT_TYPES))
        )

    print(f"pending_reminders={pending_reminders or 0}")
    print(f"pending_outbox_reminder_events={pending_outbox or 0}")


if __name__ == "__main__":
    asyncio.run(main())
