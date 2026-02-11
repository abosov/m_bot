from datetime import datetime, timezone

import pytest

from services.booking_policy import earliest_allowed_booking_date, validate_next_day_cutoff


@pytest.mark.parametrize(
    ("now_utc", "target_start_utc", "should_raise"),
    [
        (
            datetime(2026, 2, 11, 17, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
            False,
        ),
        (
            datetime(2026, 2, 11, 19, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
            True,
        ),
        (
            datetime(2026, 2, 11, 18, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc),
            False,
        ),
    ],
    ids=["before_cutoff_allows", "after_cutoff_rejects", "exact_cutoff_allows"],
)
def test_validate_next_day_cutoff_next_day_policy(
    now_utc: datetime,
    target_start_utc: datetime,
    should_raise: bool,
) -> None:
    if should_raise:
        with pytest.raises(ValueError, match="Запись и изменение доступны только на следующий день"):
            validate_next_day_cutoff(
                specialist_tz="Europe/Moscow",
                now_utc=now_utc,
                target_start_utc=target_start_utc,
            )
        return

    validate_next_day_cutoff(
        specialist_tz="Europe/Moscow",
        now_utc=now_utc,
        target_start_utc=target_start_utc,
    )


def test_validate_next_day_cutoff_rejects_not_earliest_allowed_day() -> None:
    now_utc = datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc)
    target_start_utc = datetime(2026, 2, 13, 9, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Запись и изменение доступны только на следующий день"):
        validate_next_day_cutoff(
            specialist_tz="UTC",
            now_utc=now_utc,
            target_start_utc=target_start_utc,
        )


def test_validate_next_day_cutoff_allows_day_after_tomorrow_after_cutoff() -> None:
    now_utc = datetime(2026, 2, 11, 19, 1, tzinfo=timezone.utc)  # 22:01 Europe/Moscow
    target_start_utc = datetime(2026, 2, 13, 9, 0, tzinfo=timezone.utc)

    validate_next_day_cutoff(
        specialist_tz="Europe/Moscow",
        now_utc=now_utc,
        target_start_utc=target_start_utc,
    )


def test_earliest_allowed_booking_date_respects_cutoff() -> None:
    before_cutoff = earliest_allowed_booking_date(
        specialist_tz="Europe/Moscow",
        now_utc=datetime(2026, 2, 11, 17, 0, tzinfo=timezone.utc),  # 20:00 local
    )
    after_cutoff = earliest_allowed_booking_date(
        specialist_tz="Europe/Moscow",
        now_utc=datetime(2026, 2, 11, 19, 1, tzinfo=timezone.utc),  # 22:01 local
    )

    assert str(before_cutoff) == "2026-02-12"
    assert str(after_cutoff) == "2026-02-13"
