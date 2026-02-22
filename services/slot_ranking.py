from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence


class ValidationError(ValueError):
    """Raised when slot ranking input parameters are invalid."""


def _as_timedelta_minutes(value: int | timedelta) -> timedelta:
    if isinstance(value, timedelta):
        return value
    return timedelta(minutes=value)


def _to_int_minutes(value: int | timedelta, *, field_name: str) -> int:
    if isinstance(value, timedelta):
        seconds = value.total_seconds()
        if seconds % 60 != 0:
            raise ValidationError(f"{field_name} must be in whole minutes")
        return int(seconds // 60)
    return value


def _validate_ranking_params(
    *,
    session_duration: int | timedelta,
    buffer_minutes: int | timedelta,
) -> None:
    duration_min = _to_int_minutes(session_duration, field_name="session_duration")
    buffer_min = _to_int_minutes(buffer_minutes, field_name="buffer_minutes")

    if duration_min < 15 or duration_min > 240:
        raise ValidationError("session_duration must be between 15 and 240 minutes")
    if duration_min % 5 != 0:
        raise ValidationError("session_duration must be a multiple of 5 minutes")

    if buffer_min < 0 or buffer_min > 120:
        raise ValidationError("buffer_minutes must be between 0 and 120 minutes")


def _is_adjacent(
    *,
    slot_start: datetime,
    slot_end: datetime,
    confirmed_sessions: Sequence[tuple[datetime, datetime]],
    buffer_delta: timedelta,
) -> bool:
    for confirmed_start, confirmed_end in confirmed_sessions:
        if slot_start == confirmed_end + buffer_delta:
            return True
        if slot_end + buffer_delta == confirmed_start:
            return True
    return False


def rank_slots_for_interval(
    interval_start: datetime,
    interval_end: datetime,
    candidate_starts: Iterable[datetime],
    existing_confirmed_sessions: Sequence[tuple[datetime, datetime]],
    session_duration: int | timedelta,
    buffer_minutes: int | timedelta,
    max_results: int = 6,
) -> list[datetime]:
    _validate_ranking_params(
        session_duration=session_duration,
        buffer_minutes=buffer_minutes,
    )

    duration_delta = _as_timedelta_minutes(session_duration)
    buffer_delta = _as_timedelta_minutes(buffer_minutes)

    if duration_delta <= timedelta(0) or max_results <= 0:
        return []

    has_confirmed = len(existing_confirmed_sessions) > 0

    scored: list[tuple[bool, int, datetime]] = []
    for start in candidate_starts:
        if start < interval_start or start >= interval_end:
            continue

        end = start + duration_delta
        distance_to_interval_start = int((start - interval_start).total_seconds() // 60)

        adjacent = _is_adjacent(
            slot_start=start,
            slot_end=end,
            confirmed_sessions=existing_confirmed_sessions,
            buffer_delta=buffer_delta,
        )

        # При наличии confirmed-сессий стыковка приоритетнее нестыкующихся слотов.
        adjacency_penalty = has_confirmed and not adjacent
        scored.append((adjacency_penalty, distance_to_interval_start, start))

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[2] for item in scored[:max_results]]
