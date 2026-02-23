from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import WeeklyAvailability, async_session_factory
from services.log_context import log_event
from services.specialist_defaults import DEFAULT_WORKING_DAYS, DEFAULT_WORKING_INTERVALS


logger = logging.getLogger(__name__)


def _validate_weekday(weekday: int) -> None:
    if weekday < 0 or weekday > 6:
        raise ValueError("weekday must be in range 0..6")


def _build_default_row(*, specialist_id: UUID, weekday: int) -> WeeklyAvailability:
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
    return row


async def _ensure_weekly_rows(session: AsyncSession, specialist_id: UUID) -> tuple[list[WeeklyAvailability], bool]:
    rows = (
        await session.execute(
            select(WeeklyAvailability)
            .where(WeeklyAvailability.specialist_id == specialist_id)
            .order_by(WeeklyAvailability.weekday.asc())
        )
    ).scalars().all()

    rows_by_weekday = {row.weekday: row for row in rows}
    changed = False
    for weekday in range(7):
        if weekday in rows_by_weekday:
            continue
        row = _build_default_row(specialist_id=specialist_id, weekday=weekday)
        session.add(row)
        rows.append(row)
        rows_by_weekday[weekday] = row
        changed = True

    if changed:
        await session.flush()

    return rows, changed


async def get_working_days(specialist_id: UUID) -> set[int]:
    async with async_session_factory() as session:
        rows, changed = await _ensure_weekly_rows(session, specialist_id)
        if changed:
            await session.commit()
        return {row.weekday for row in rows if row.is_working}


async def toggle_working_day(specialist_id: UUID, weekday: int) -> set[int]:
    _validate_weekday(weekday)

    async with async_session_factory() as session:
        rows, _ = await _ensure_weekly_rows(session, specialist_id)
        row_by_weekday = {row.weekday: row for row in rows}
        row = row_by_weekday[weekday]
        row.is_working = not row.is_working
        await session.commit()

        log_event(
            logger,
            logging.INFO,
            event="weekly_availability_day_toggled",
            specialist_id=str(specialist_id),
            weekday=weekday,
            is_working=row.is_working,
        )

        return {entry.weekday for entry in rows if entry.is_working}


async def set_working_day(specialist_id: UUID, weekday: int, is_working: bool) -> None:
    _validate_weekday(weekday)

    async with async_session_factory() as session:
        rows, _ = await _ensure_weekly_rows(session, specialist_id)
        row_by_weekday = {row.weekday: row for row in rows}
        row_by_weekday[weekday].is_working = is_working
        await session.commit()
