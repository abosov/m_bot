from datetime import time

from services.schedule_utils import is_time_range_allowed, merge_intervals


def test_merge_intervals_merges_adjacent_ranges() -> None:
    intervals = [(time(13, 0), time(17, 0)), (time(17, 0), time(21, 0))]

    result = merge_intervals(intervals)

    assert result == [(time(13, 0), time(21, 0))]


def test_is_time_range_allowed_for_adjacent_ranges() -> None:
    intervals = [(time(13, 0), time(17, 0)), (time(17, 0), time(21, 0))]

    result = is_time_range_allowed(start=time(16, 30), end=time(17, 30), intervals=intervals)

    assert result is True


def test_is_time_range_not_allowed_for_gap_between_ranges() -> None:
    intervals = [(time(13, 0), time(17, 0)), (time(18, 0), time(21, 0))]

    result = is_time_range_allowed(start=time(16, 30), end=time(17, 30), intervals=intervals)

    assert result is False
