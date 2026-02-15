from datetime import datetime

from services.slot_ranking import rank_slots_for_interval


def test_rank_slots_without_existing_confirmed_prefers_early_start() -> None:
    interval_start = datetime(2026, 2, 11, 9, 0)
    interval_end = datetime(2026, 2, 11, 12, 0)
    candidates = [
        datetime(2026, 2, 11, 9, 30),
        datetime(2026, 2, 11, 11, 0),
        datetime(2026, 2, 11, 9, 0),
        datetime(2026, 2, 11, 10, 0),
    ]

    ranked = rank_slots_for_interval(
        interval_start=interval_start,
        interval_end=interval_end,
        candidate_starts=candidates,
        existing_confirmed_sessions=[],
        session_duration=60,
        buffer_minutes=15,
        max_results=4,
    )

    assert ranked == [
        datetime(2026, 2, 11, 9, 0),
        datetime(2026, 2, 11, 9, 30),
        datetime(2026, 2, 11, 10, 0),
        datetime(2026, 2, 11, 11, 0),
    ]


def test_rank_slots_prioritizes_adjacent_slot_after_confirmed() -> None:
    interval_start = datetime(2026, 2, 11, 13, 0)
    interval_end = datetime(2026, 2, 11, 18, 0)
    candidates = [
        datetime(2026, 2, 11, 13, 0),
        datetime(2026, 2, 11, 13, 30),
        datetime(2026, 2, 11, 15, 15),
    ]
    confirmed = [(datetime(2026, 2, 11, 14, 0), datetime(2026, 2, 11, 15, 0))]

    ranked = rank_slots_for_interval(
        interval_start=interval_start,
        interval_end=interval_end,
        candidate_starts=candidates,
        existing_confirmed_sessions=confirmed,
        session_duration=60,
        buffer_minutes=15,
        max_results=3,
    )

    assert ranked == [
        datetime(2026, 2, 11, 15, 15),
        datetime(2026, 2, 11, 13, 0),
        datetime(2026, 2, 11, 13, 30),
    ]


def test_rank_slots_prioritizes_adjacent_slot_before_confirmed() -> None:
    interval_start = datetime(2026, 2, 11, 12, 0)
    interval_end = datetime(2026, 2, 11, 18, 0)
    candidates = [
        datetime(2026, 2, 11, 12, 0),
        datetime(2026, 2, 11, 12, 45),
        datetime(2026, 2, 11, 13, 0),
    ]
    confirmed = [(datetime(2026, 2, 11, 14, 0), datetime(2026, 2, 11, 15, 0))]

    ranked = rank_slots_for_interval(
        interval_start=interval_start,
        interval_end=interval_end,
        candidate_starts=candidates,
        existing_confirmed_sessions=confirmed,
        session_duration=60,
        buffer_minutes=15,
        max_results=3,
    )

    assert ranked == [
        datetime(2026, 2, 11, 12, 45),
        datetime(2026, 2, 11, 12, 0),
        datetime(2026, 2, 11, 13, 0),
    ]


def test_rank_slots_with_multiple_confirmed_sessions() -> None:
    interval_start = datetime(2026, 2, 11, 8, 0)
    interval_end = datetime(2026, 2, 11, 18, 0)
    candidates = [
        datetime(2026, 2, 11, 9, 45),
        datetime(2026, 2, 11, 12, 15),
        datetime(2026, 2, 11, 15, 45),
        datetime(2026, 2, 11, 8, 0),
    ]
    confirmed = [
        (datetime(2026, 2, 11, 11, 0), datetime(2026, 2, 11, 12, 0)),
        (datetime(2026, 2, 11, 13, 30), datetime(2026, 2, 11, 14, 30)),
    ]

    ranked = rank_slots_for_interval(
        interval_start=interval_start,
        interval_end=interval_end,
        candidate_starts=candidates,
        existing_confirmed_sessions=confirmed,
        session_duration=60,
        buffer_minutes=15,
        max_results=4,
    )

    assert ranked == [
        datetime(2026, 2, 11, 9, 45),
        datetime(2026, 2, 11, 12, 15),
        datetime(2026, 2, 11, 8, 0),
        datetime(2026, 2, 11, 15, 45),
    ]
