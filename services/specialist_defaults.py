from __future__ import annotations

from datetime import time
from typing import Iterable

from sqlalchemy import select

from database import SpecialistAuthTelegram, SpecialistProfile, WeeklyAvailability

DEFAULT_DURATION_MIN = 60
DEFAULT_BUFFER_MIN = 10
DEFAULT_CANCEL_WINDOW_HOURS = 12
DEFAULT_MAX_SESSIONS_PER_DAY = 4
DEFAULT_SLOT_STEP_MIN = 15
ALLOWED_SLOT_STEPS_MIN = {60, 30, 15, 10}
DEFAULT_TIMEZONE = "UTC"

DEFAULT_WORKING_DAYS = {0, 1, 2, 3, 4}
DEFAULT_WORKING_INTERVALS = [
    (time(9, 0), time(12, 0)),
    (time(13, 0), time(17, 0)),
    (time(17, 0), time(21, 0)),
]


async def apply_specialist_defaults_if_missing(
    session,
    specialist_id,
    *,
    preferred_timezone: str | None = None,
) -> None:
    timezone = (preferred_timezone or "").strip() or DEFAULT_TIMEZONE

    profile = await session.get(SpecialistProfile, specialist_id)
    if profile is None:
        auth = await session.get(SpecialistAuthTelegram, specialist_id)
        owner_tg_user_id = auth.tg_user_id if auth else 0
        owner_tg_username = auth.tg_username if auth else None
        profile = SpecialistProfile(
            specialist_id=specialist_id,
            public_name="Специалист",
            owner_tg_user_id=owner_tg_user_id,
            owner_tg_username=owner_tg_username,
            specialist_timezone=timezone,
            session_duration_min=DEFAULT_DURATION_MIN,
            session_buffer_min=DEFAULT_BUFFER_MIN,
            cancel_window_hours=DEFAULT_CANCEL_WINDOW_HOURS,
            max_sessions_per_day=DEFAULT_MAX_SESSIONS_PER_DAY,
            slot_step_min=DEFAULT_SLOT_STEP_MIN,
        )
        session.add(profile)
    else:
        if not (profile.specialist_timezone or "").strip():
            profile.specialist_timezone = timezone

        if profile.session_duration_min is None or profile.session_duration_min <= 0:
            profile.session_duration_min = DEFAULT_DURATION_MIN
        if profile.session_buffer_min is None or profile.session_buffer_min < 0:
            profile.session_buffer_min = DEFAULT_BUFFER_MIN
        if profile.cancel_window_hours is None or profile.cancel_window_hours <= 0:
            profile.cancel_window_hours = DEFAULT_CANCEL_WINDOW_HOURS
        if profile.max_sessions_per_day is None or profile.max_sessions_per_day <= 0:
            profile.max_sessions_per_day = DEFAULT_MAX_SESSIONS_PER_DAY
        if profile.slot_step_min is None or profile.slot_step_min not in ALLOWED_SLOT_STEPS_MIN:
            profile.slot_step_min = DEFAULT_SLOT_STEP_MIN

    rows = (
        await session.execute(
            select(WeeklyAvailability)
            .where(WeeklyAvailability.specialist_id == specialist_id)
            .order_by(WeeklyAvailability.weekday.asc())
        )
    ).scalars().all()

    if not _has_complete_weekly_rows(rows):
        for weekday in range(7):
            is_working = weekday in DEFAULT_WORKING_DAYS
            row = WeeklyAvailability(
                specialist_id=specialist_id,
                weekday=weekday,
                is_working=is_working,
            )
            if is_working:
                row.interval_1_start, row.interval_1_end = DEFAULT_WORKING_INTERVALS[0]
                row.interval_2_start, row.interval_2_end = DEFAULT_WORKING_INTERVALS[1]
                row.interval_3_start, row.interval_3_end = DEFAULT_WORKING_INTERVALS[2]
            session.add(row)

    await session.flush()


def _has_complete_weekly_rows(rows: Iterable[WeeklyAvailability]) -> bool:
    weekdays = {row.weekday for row in rows}
    return len(weekdays) == 7
