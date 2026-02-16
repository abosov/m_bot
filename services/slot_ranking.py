from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence


def _as_timedelta_minutes(value: int | timedelta) -> timedelta:
    if isinstance(value, timedelta):
        return value
    return timedelta(minutes=value)


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
