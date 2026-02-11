from __future__ import annotations

from datetime import date, datetime, time

from services.slot_step import iter_slot_starts


def merge_intervals(intervals: list[tuple[time, time]]) -> list[tuple[time, time]]:
    """
    Сортирует интервалы по start и склеивает:
    - пересекающиеся
    - и стыкующиеся (end == next_start).

    Правило: интервалы «стык-в-стык» объединяются в единый диапазон
    (например, 13:00–17:00 + 17:00–21:00 -> 13:00–21:00).
    Возвращает список объединённых интервалов.
    """
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged: list[tuple[time, time]] = [sorted_intervals[0]]

    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
            continue
        merged.append((current_start, current_end))

    return merged


def is_time_range_allowed(
    *,
    start: time,
    end: time,
    intervals: list[tuple[time, time]],
) -> bool:
    """
    True если [start,end] полностью попадает в один из объединённых интервалов.
    Важно: если интервалы 13:00–17:00 и 17:00–21:00, то сессия 16:30–17:30 должна быть разрешена.
    """
    for interval_start, interval_end in merge_intervals(intervals):
        if start >= interval_start and end <= interval_end:
            return True
    return False


def generate_day_slot_starts(
    *,
    target_date: date,
    intervals: list[tuple[time, time]],
    session_duration_min: int,
    session_buffer_min: int,
    slot_step_min: int,
) -> list[time]:
    """
    Генерирует допустимые начала слотов в пределах дня с учётом:
    - объединения стыкующихся интервалов,
    - длительности сессии,
    - буфера между сессиями,
    - шага начала слотов.
    """
    effective_duration_min = session_duration_min + max(session_buffer_min, 0)
    if effective_duration_min <= 0:
        return []

    result: list[time] = []
    seen: set[time] = set()

    for interval_start, interval_end in merge_intervals(intervals):
        dt_start = datetime.combine(target_date, interval_start)
        dt_end = datetime.combine(target_date, interval_end)
        for slot_start in iter_slot_starts(
            dt_start,
            dt_end,
            step_min=slot_step_min,
            duration_min=effective_duration_min,
        ):
            slot_time = slot_start.time()
            if slot_time in seen:
                continue
            seen.add(slot_time)
            result.append(slot_time)

    return result
