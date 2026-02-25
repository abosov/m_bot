from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import select

from database import SpecialistWorkingInterval, async_session_factory
from services.working_intervals_domain import normalize_intervals
from services.working_intervals_repository import WorkingIntervalsByIdx, WorkingIntervalsRepository

DEFAULT_WORKING_INTERVALS_MIN = {
    1: (540, 720),
    2: (780, 1020),
    3: (1020, 1260),
}


class WorkingIntervalsValidationError(ValueError):
    pass


async def ensure_default_working_intervals(specialist_id: UUID) -> bool:
    """Ensure specialist has rows idx=1..3 in specialist_working_intervals.

    Returns True when at least one missing row was created.
    """
    async with async_session_factory() as session:
        existing_rows = (
            await session.execute(
                select(SpecialistWorkingInterval.idx).where(
                    SpecialistWorkingInterval.specialist_id == specialist_id
                )
            )
        ).scalars().all()

        existing_idx = set(existing_rows)
        changed = False

        for idx, (start_min, end_min) in DEFAULT_WORKING_INTERVALS_MIN.items():
            if idx in existing_idx:
                continue
            session.add(
                SpecialistWorkingInterval(
                    specialist_id=specialist_id,
                    idx=idx,
                    start_min=start_min,
                    end_min=end_min,
                )
            )
            changed = True

        if changed:
            await session.commit()

        return changed


async def apply_interval_edit(
    specialist_id: UUID,
    idx: int,
    new_start_min: int | None,
    new_end_min: int | None,
    action: Literal["set", "disable"],
) -> WorkingIntervalsByIdx:
    if idx not in {1, 2, 3}:
        raise WorkingIntervalsValidationError("idx must be one of 1,2,3")

    if action not in {"set", "disable"}:
        raise WorkingIntervalsValidationError("action must be 'set' or 'disable'")

    if action == "set":
        if new_start_min is None or new_end_min is None:
            raise WorkingIntervalsValidationError("start and end are required for action='set'")
        if not (0 <= new_start_min < new_end_min <= 1440):
            raise WorkingIntervalsValidationError("expected 0 <= start < end <= 1440")

    await ensure_default_working_intervals(specialist_id)

    repository = WorkingIntervalsRepository()
    intervals = await repository.get_working_intervals(specialist_id)

    if action == "disable":
        intervals[idx] = (None, None)
    else:
        intervals[idx] = (new_start_min, new_end_min)

    normalized = normalize_intervals(intervals, edited_idx=idx)
    await repository.upsert_working_intervals(specialist_id, normalized)
    return normalized
