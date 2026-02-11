from datetime import date, time

from services.schedule_utils import generate_day_slot_starts, is_time_range_allowed, merge_intervals


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


def test_generate_day_slot_starts_merges_adjacent_ranges_without_buffer() -> None:
    starts = generate_day_slot_starts(
        target_date=date(2026, 2, 11),
        intervals=[(time(13, 0), time(17, 0)), (time(17, 0), time(21, 0))],
        session_duration_min=60,
        session_buffer_min=0,
        slot_step_min=15,
    )

    assert time(16, 30) in starts
    assert time(17, 0) in starts
    assert starts[-1] == time(20, 0)


def test_generate_day_slot_starts_merges_adjacent_ranges_with_buffer() -> None:
    starts = generate_day_slot_starts(
        target_date=date(2026, 2, 11),
        intervals=[(time(13, 0), time(17, 0)), (time(17, 0), time(21, 0))],
        session_duration_min=60,
        session_buffer_min=10,
        slot_step_min=15,
    )

    assert time(16, 0) in starts
    assert time(16, 30) in starts
    assert starts[-1] == time(19, 45)
