from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    Appointment,
    AppointmentReminder,
    BookingState,
    ReminderType,
    async_session_factory,
)
from services.log_context import log_event
from services.outbox import emit_domain_event

logger = logging.getLogger(__name__)

SCHEDULER_POLL_INTERVAL_SEC = 60.0
REMINDER_WINDOW_DELTA = timedelta(minutes=3)


@dataclass(frozen=True)
class ReminderSpec:
    reminder_type: ReminderType
    lead_time: timedelta
    event_type: str


REMINDER_SPECS: tuple[ReminderSpec, ...] = (
    ReminderSpec(ReminderType.h24, timedelta(hours=24), "appointment_client_reminder_24h"),
    ReminderSpec(ReminderType.h2, timedelta(hours=2), "appointment_client_reminder_2h"),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def insert_reminder_once(
    session: AsyncSession,
    *,
    appointment: Appointment,
    reminder_type: ReminderType,
    due_at_utc: datetime,
) -> bool:
    reminder = AppointmentReminder(
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        reminder_type=reminder_type,
        due_at_utc=due_at_utc,
        created_at_utc=datetime.now(timezone.utc),
    )
    try:
        async with session.begin_nested():
            session.add(reminder)
            await session.flush()
        return True
    except IntegrityError as exc:
        message = str(exc).lower()
        if "unique" in message or "duplicate" in message:
            return False
        raise


async def run_scheduler_reminder_scan(now_utc: datetime | None = None) -> dict[str, int]:
    now = now_utc or utc_now()
    created_reminders = 0
    emitted_events = 0

    async with async_session_factory() as session:
        async with session.begin():
            for spec in REMINDER_SPECS:
                window_start = now + spec.lead_time - REMINDER_WINDOW_DELTA
                window_end = now + spec.lead_time + REMINDER_WINDOW_DELTA
                result = await session.execute(
                    select(Appointment)
                    .where(
                        and_(
                            Appointment.booking_state == BookingState.confirmed,
                            Appointment.start_at_utc >= window_start,
                            Appointment.start_at_utc <= window_end,
                        )
                    )
                    .order_by(Appointment.start_at_utc.asc())
                )
                appointments = result.scalars().all()

                for appointment in appointments:
                    reminder_due_at = appointment.start_at_utc - spec.lead_time
                    inserted = await insert_reminder_once(
                        session,
                        appointment=appointment,
                        reminder_type=spec.reminder_type,
                        due_at_utc=reminder_due_at,
                    )
                    if not inserted:
                        continue

                    created_reminders += 1
                    payload = {
                        "appointment_id": str(appointment.appointment_id),
                        "specialist_id": str(appointment.specialist_id),
                        "client_id": str(appointment.client_id),
                        "start_at_utc": appointment.start_at_utc.isoformat(),
                        "end_at_utc": appointment.end_at_utc.isoformat(),
                    }
                    await emit_domain_event(session, spec.event_type, payload)
                    emitted_events += 1

                log_event(
                    logger,
                    logging.INFO,
                    event="scheduler_reminder_scan_window",
                    reminder_type=spec.reminder_type.value,
                    window_start=window_start.isoformat(),
                    window_end=window_end.isoformat(),
                    matched_appointments=len(appointments),
                )

    log_event(
        logger,
        logging.INFO,
        event="scheduler_reminder_scan_completed",
        created_reminders=created_reminders,
        emitted_events=emitted_events,
    )
    return {"created_reminders": created_reminders, "emitted_events": emitted_events}


async def scheduler_task() -> None:
    logger.info("scheduler_task started")
    try:
        while True:
            try:
                await run_scheduler_reminder_scan()
            except Exception as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    event="scheduler_cycle_failed",
                    exception_class=exc.__class__.__name__,
                )
            await asyncio.sleep(SCHEDULER_POLL_INTERVAL_SEC)
    except asyncio.CancelledError:
        logger.info("scheduler_task stopped")
        raise
