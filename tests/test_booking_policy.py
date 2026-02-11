from datetime import datetime, timezone

import pytest

from services.booking_policy import validate_next_day_cutoff


def test_validate_next_day_cutoff_allows_next_day_before_cutoff() -> None:
    now_utc = datetime(2026, 2, 11, 17, 0, tzinfo=timezone.utc)  # 20:00 Europe/Moscow
    target_start_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)  # 12:00 Europe/Moscow

    validate_next_day_cutoff(
        specialist_tz="Europe/Moscow",
        now_utc=now_utc,
        target_start_utc=target_start_utc,
    )


def test_validate_next_day_cutoff_rejects_after_cutoff() -> None:
    now_utc = datetime(2026, 2, 11, 19, 0, tzinfo=timezone.utc)  # 22:00 Europe/Moscow
    target_start_utc = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Запись и изменение доступны только на следующий день"):
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
