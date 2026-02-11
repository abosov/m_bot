from __future__ import annotations

from datetime import time


def merge_intervals(intervals: list[tuple[time, time]]) -> list[tuple[time, time]]:
    """
    Сортирует интервалы по start и склеивает:
    - пересекающиеся
    - и стыкующиеся (end == next_start)
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
    # Для будущего сценария бронирования/переноса: перед проверкой доступности
    # обязательно используем объединённые интервалы, чтобы корректно
    # обрабатывать стыки соседних слотов.
    for interval_start, interval_end in merge_intervals(intervals):
        if start >= interval_start and end <= interval_end:
            return True
    return False
