from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timezone

from sqlalchemy import select

from database import Appointment, BookingState, SpecialistWorkingHours, async_session_factory


logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


async def invalidate_availability_cache(specialist_id: uuid.UUID) -> None:
    """Invalidate availability cache for specialist.

    Current implementation is a no-op because availability slots are calculated on read.
    """
    logger.debug("event=availability_cache_invalidate specialist_id=%s", specialist_id)


async def get_specialist_schedule(specialist_id: uuid.UUID) -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[tuple[time, time]]] = {weekday: [] for weekday in range(7)}

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                SpecialistWorkingHours.weekday,
                SpecialistWorkingHours.start_time,
                SpecialistWorkingHours.end_time,
            ).where(SpecialistWorkingHours.specialist_id == specialist_id)
        )

    for weekday, start_time, end_time in result.all():
        grouped[int(weekday)].append((start_time, end_time))

    schedule: dict[int, list[dict[str, str]]] = {weekday: [] for weekday in range(7)}
    for weekday in range(7):
        intervals = sorted(grouped[weekday], key=lambda pair: pair[0])
        schedule[weekday] = [
            {
                "start": start_time.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
            }
            for start_time, end_time in intervals
        ]

    return schedule


async def validate_schedule_interval(
    specialist_id: uuid.UUID,
    weekday: int,
    start_time: time,
    end_time: time,
) -> None:
    if start_time >= end_time:
        raise ValidationError("start_time must be less than end_time")

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                SpecialistWorkingHours.start_time,
                SpecialistWorkingHours.end_time,
            ).where(
                SpecialistWorkingHours.specialist_id == specialist_id,
                SpecialistWorkingHours.weekday == weekday,
            )
        )

    for existing_start, existing_end in result.all():
        if start_time < existing_end and existing_start < end_time:
            raise ValidationError("interval overlaps with existing schedule interval")


async def add_working_interval(
    specialist_id: uuid.UUID,
    weekday: int,
    start_time: time,
    end_time: time,
) -> dict[int, list[dict[str, str]]]:
    await validate_schedule_interval(specialist_id, weekday, start_time, end_time)

    async with async_session_factory() as session:
        async with session.begin():
            session.add(
                SpecialistWorkingHours(
                    specialist_id=specialist_id,
                    weekday=weekday,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

    await invalidate_availability_cache(specialist_id)
    await _warn_future_confirmed_outside_schedule(specialist_id)
    return await get_specialist_schedule(specialist_id)


async def delete_working_interval(interval_id: uuid.UUID, specialist_id: uuid.UUID) -> dict[int, list[dict[str, str]]]:
    async with async_session_factory() as session:
        async with session.begin():
            interval = (
                await session.execute(
                    select(SpecialistWorkingHours).where(
                        SpecialistWorkingHours.id == interval_id,
                        SpecialistWorkingHours.specialist_id == specialist_id,
                    )
                )
            ).scalar_one_or_none()

            if interval is None:
                raise ValidationError("working interval does not belong to specialist")

            await session.delete(interval)

    await invalidate_availability_cache(specialist_id)
    await _warn_future_confirmed_outside_schedule(specialist_id)
    return await get_specialist_schedule(specialist_id)


async def _warn_future_confirmed_outside_schedule(specialist_id: uuid.UUID) -> None:
    schedule = await get_specialist_schedule(specialist_id)
    intervals_by_weekday: dict[int, list[tuple[time, time]]] = {weekday: [] for weekday in range(7)}
    for weekday in range(7):
        intervals_by_weekday[weekday] = [
            (datetime.strptime(item["start"], "%H:%M").time(), datetime.strptime(item["end"], "%H:%M").time())
            for item in schedule[weekday]
        ]

    now_utc = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        confirmed = (
            await session.execute(
                select(Appointment.start_at_utc, Appointment.end_at_utc).where(
                    Appointment.specialist_id == specialist_id,
                    Appointment.booking_state == BookingState.confirmed,
                    Appointment.start_at_utc >= now_utc,
                )
            )
        ).all()

    became_unavailable = 0
    for start_at_utc, end_at_utc in confirmed:
        weekday = start_at_utc.weekday()
        day_start = start_at_utc.time().replace(tzinfo=None)
        day_end = end_at_utc.time().replace(tzinfo=None)
        if not any(day_start >= interval_start and day_end <= interval_end for interval_start, interval_end in intervals_by_weekday[weekday]):
            became_unavailable += 1

    if became_unavailable > 0:
        logger.warning(
            "event=working_hours_change_future_slots_unavailable specialist_id=%s confirmed_sessions_affected=%s",
            specialist_id,
            became_unavailable,
        )
