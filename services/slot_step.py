from __future__ import annotations

from datetime import datetime, timedelta


_MIN_SLOT_STEP = 5


def _validate_step(step_min: int) -> None:
    if step_min < _MIN_SLOT_STEP:
        raise ValueError("step_min must be >= 5")
    if step_min % 5 != 0:
        raise ValueError("step_min must be a multiple of 5")


def is_aligned_to_step(dt_local: datetime, step_min: int) -> bool:
    _validate_step(step_min)
    return dt_local.minute % step_min == 0 and dt_local.second == 0 and dt_local.microsecond == 0


def round_up_to_step(dt_local: datetime, step_min: int) -> datetime:
    _validate_step(step_min)

    normalized = dt_local.replace(second=0, microsecond=0)
    if normalized == dt_local and normalized.minute % step_min == 0:
        return normalized

    remainder = normalized.minute % step_min
    if remainder == 0:
        return normalized

    return normalized + timedelta(minutes=step_min - remainder)


def iter_slot_starts(
    interval_start_local: datetime,
    interval_end_local: datetime,
    *,
    step_min: int,
    duration_min: int,
) -> list[datetime]:
    _validate_step(step_min)

    if duration_min <= 0:
        return []

    slot_starts: list[datetime] = []
    current_start = round_up_to_step(interval_start_local, step_min)
    duration_delta = timedelta(minutes=duration_min)
    step_delta = timedelta(minutes=step_min)

    while current_start + duration_delta <= interval_end_local:
        slot_starts.append(current_start)
        current_start += step_delta

    return slot_starts
