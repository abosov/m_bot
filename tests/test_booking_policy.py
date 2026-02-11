from datetime import datetime, timezone

import pytest

from services.booking_policy import validate_next_day_cutoff


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


def test_validate_next_day_cutoff_rejects_not_next_day() -> None:
    now_utc = datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc)
    target_start_utc = datetime(2026, 2, 13, 9, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Запись и изменение доступны только на следующий день"):
        validate_next_day_cutoff(
            specialist_tz="UTC",
            now_utc=now_utc,
            target_start_utc=target_start_utc,
        )
