from datetime import datetime

from services.slot_step import is_aligned_to_step, iter_slot_starts, round_up_to_step


def test_is_aligned_to_step_for_15_minutes() -> None:
    assert is_aligned_to_step(datetime(2026, 2, 11, 9, 0), 15) is True
    assert is_aligned_to_step(datetime(2026, 2, 11, 9, 15), 15) is True
    assert is_aligned_to_step(datetime(2026, 2, 11, 9, 30), 15) is True
    assert is_aligned_to_step(datetime(2026, 2, 11, 9, 45), 15) is True
    assert is_aligned_to_step(datetime(2026, 2, 11, 9, 10), 15) is False


def test_round_up_to_step_for_15_minutes() -> None:
    result = round_up_to_step(datetime(2026, 2, 11, 10, 7), 15)

    assert result == datetime(2026, 2, 11, 10, 15)


def test_iter_slot_starts_for_15_step_and_30_duration() -> None:
    result = iter_slot_starts(
        datetime(2026, 2, 11, 9, 0),
        datetime(2026, 2, 11, 10, 0),
        step_min=15,
        duration_min=30,
    )

    assert result == [
        datetime(2026, 2, 11, 9, 0),
        datetime(2026, 2, 11, 9, 15),
        datetime(2026, 2, 11, 9, 30),
    ]


def test_iter_slot_starts_for_60_step() -> None:
    result = iter_slot_starts(
        datetime(2026, 2, 11, 9, 0),
        datetime(2026, 2, 11, 10, 0),
        step_min=60,
        duration_min=30,
    )

    assert result == [datetime(2026, 2, 11, 9, 0)]
