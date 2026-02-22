from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select

from database import Appointment, BookingState, SpecialistProfile, SpecialistWorkingHours, async_session_factory
from services.specialist_defaults import (
    DEFAULT_BUFFER_MIN,
    DEFAULT_DURATION_MIN,
    DEFAULT_MAX_SESSIONS_PER_DAY,
    DEFAULT_SLOT_STEP_MIN,
    DEFAULT_WORKING_DAYS,
    DEFAULT_WORKING_INTERVALS,
)


logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


async def invalidate_availability_cache(specialist_id: uuid.UUID) -> None:
    """Invalidate availability cache for specialist.

    Current implementation is a no-op because availability slots are calculated on read.
    """
    logger.debug("event=availability_cache_invalidate specialist_id=%s", specialist_id)


def _validate_timezone(value: str) -> str:
    timezone_name = value.strip()
    if not timezone_name:
        raise ValidationError("timezone must not be empty")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValidationError(f"timezone does not exist: {timezone_name}") from exc
    return timezone_name


async def update_specialist_timezone(
    specialist_id: uuid.UUID,
    timezone_name: str,
) -> dict[str, str]:
    valid_timezone = _validate_timezone(timezone_name)

    async with async_session_factory() as session:
        async with session.begin():
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValidationError("specialist profile not found")

            profile.specialist_timezone = valid_timezone

        updated_timezone = profile.specialist_timezone

    await invalidate_availability_cache(specialist_id)

    return {"specialist_timezone": updated_timezone}


def _validate_session_settings(duration: int, buffer: int) -> None:
    if duration < 15 or duration > 240:
        raise ValidationError("session_duration must be between 15 and 240 minutes")
    if duration % 5 != 0:
        raise ValidationError("session_duration must be a multiple of 5 minutes")
    if buffer < 0 or buffer > 120:
        raise ValidationError("buffer_minutes must be between 0 and 120 minutes")


async def update_session_settings(
    specialist_id: uuid.UUID,
    duration: int,
    buffer: int,
) -> dict[str, int]:
    _validate_session_settings(duration, buffer)

    async with async_session_factory() as session:
        async with session.begin():
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValidationError("specialist profile not found")

            profile.session_duration_min = duration
            profile.session_buffer_min = buffer

        updated_duration = profile.session_duration_min
        updated_buffer = profile.session_buffer_min

    await invalidate_availability_cache(specialist_id)

    return {
        "session_duration_min": updated_duration,
        "session_buffer_min": updated_buffer,
    }



def _validate_limits(max_per_day: int, slot_step: int, session_duration: int) -> None:
    if max_per_day < 1 or max_per_day > 20:
        raise ValidationError("max_sessions_per_day must be between 1 and 20")
    if slot_step < 5:
        raise ValidationError("slot_step_minutes must be >= 5")
    if slot_step > session_duration:
        raise ValidationError("slot_step_minutes must be <= session_duration")
    if slot_step % 5 != 0:
        raise ValidationError("slot_step_minutes must be a multiple of 5")


async def update_limits(
    specialist_id: uuid.UUID,
    max_per_day: int,
    slot_step: int,
) -> dict[str, int]:
    async with async_session_factory() as session:
        async with session.begin():
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValidationError("specialist profile not found")

            _validate_limits(max_per_day=max_per_day, slot_step=slot_step, session_duration=profile.session_duration_min)

            profile.max_sessions_per_day = max_per_day
            profile.slot_step_min = slot_step

        updated_max = profile.max_sessions_per_day
        updated_step = profile.slot_step_min

    await invalidate_availability_cache(specialist_id)

    return {
        "max_sessions_per_day": updated_max,
        "slot_step_min": updated_step,
    }


async def reset_specialist_settings_to_default(specialist_id: uuid.UUID) -> dict[str, int | dict[int, list[dict[str, str]]]]:
    async with async_session_factory() as session:
        async with session.begin():
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValidationError("specialist profile not found")

            profile.session_duration_min = DEFAULT_DURATION_MIN
            profile.session_buffer_min = DEFAULT_BUFFER_MIN
            profile.slot_step_min = DEFAULT_SLOT_STEP_MIN
            profile.max_sessions_per_day = DEFAULT_MAX_SESSIONS_PER_DAY

            existing_intervals = (
                await session.execute(
                    select(SpecialistWorkingHours).where(SpecialistWorkingHours.specialist_id == specialist_id)
                )
            ).scalars().all()
            for interval in existing_intervals:
                await session.delete(interval)

            for weekday in sorted(DEFAULT_WORKING_DAYS):
                for start_time, end_time in DEFAULT_WORKING_INTERVALS:
                    session.add(
                        SpecialistWorkingHours(
                            specialist_id=specialist_id,
                            weekday=weekday,
                            start_time=start_time,
                            end_time=end_time,
                        )
                    )

        updated_duration = profile.session_duration_min
        updated_buffer = profile.session_buffer_min
        updated_slot_step = profile.slot_step_min
        updated_max_per_day = profile.max_sessions_per_day

    await invalidate_availability_cache(specialist_id)

    return {
        "session_duration_min": updated_duration,
        "session_buffer_min": updated_buffer,
        "slot_step_min": updated_slot_step,
        "max_sessions_per_day": updated_max_per_day,
        "schedule": await get_specialist_schedule(specialist_id),
    }


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
