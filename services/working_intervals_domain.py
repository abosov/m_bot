from __future__ import annotations

from typing import Optional

WorkingIntervalPair = tuple[Optional[int], Optional[int]]
WorkingIntervalsByIdx = dict[int, WorkingIntervalPair]


def normalize_intervals(intervals: WorkingIntervalsByIdx, edited_idx: int) -> WorkingIntervalsByIdx:
    if edited_idx not in {1, 2, 3}:
        raise ValueError("edited_idx must be one of 1, 2, 3")

    def _normalized_pair(value: WorkingIntervalPair) -> WorkingIntervalPair:
        start_min, end_min = value
        if start_min is None or end_min is None:
            return (None, None)
        return (start_min, end_min)

    normalized: WorkingIntervalsByIdx = {
        1: _normalized_pair(intervals.get(1, (None, None))),
        2: _normalized_pair(intervals.get(2, (None, None))),
        3: _normalized_pair(intervals.get(3, (None, None))),
    }

    def _is_active(idx: int) -> bool:
        start_min, end_min = normalized[idx]
        return start_min is not None and end_min is not None

    def _prev_active_idx(idx: int) -> int | None:
        for candidate in range(idx - 1, 0, -1):
            if _is_active(candidate):
                return candidate
        return None

    def _next_active_idx(idx: int) -> int | None:
        for candidate in range(idx + 1, 4):
            if _is_active(candidate):
                return candidate
        return None

    def _disable(idx: int) -> None:
        normalized[idx] = (None, None)

    def _resolve_right(left_idx: int) -> bool:
        if not _is_active(left_idx):
            return False

        right_idx = _next_active_idx(left_idx)
        if right_idx is None:
            return False

        left_start, left_end = normalized[left_idx]
        right_start, right_end = normalized[right_idx]
        assert left_start is not None and left_end is not None
        assert right_start is not None and right_end is not None

        if left_end <= right_start:
            return False

        new_right_start = left_end
        if new_right_start >= right_end:
            _disable(right_idx)
            return True

        normalized[right_idx] = (new_right_start, right_end)
        return True

    def _resolve_left(right_idx: int) -> bool:
        if not _is_active(right_idx):
            return False

        left_idx = _prev_active_idx(right_idx)
        if left_idx is None:
            return False

        left_start, left_end = normalized[left_idx]
        right_start, right_end = normalized[right_idx]
        assert left_start is not None and left_end is not None
        assert right_start is not None and right_end is not None

        if left_end <= right_start:
            return False

        new_left_end = right_start
        if left_start >= new_left_end:
            _disable(left_idx)
            return True

        normalized[left_idx] = (left_start, new_left_end)
        return True

    for _ in range(3):
        changed = False

        cursor = edited_idx
        while True:
            changed = _resolve_right(cursor) or changed
            next_active = _next_active_idx(cursor)
            if next_active is None:
                break
            cursor = next_active

        cursor = edited_idx
        while True:
            changed = _resolve_left(cursor) or changed
            prev_active = _prev_active_idx(cursor)
            if prev_active is None:
                break
            cursor = prev_active

        if not changed:
            break

    return normalized
