from datetime import datetime, timedelta, timezone

import pytest

from services.booking_policy import validate_min_hours_before_start


def test_validate_min_hours_before_start_allows_exact_boundary() -> None:
    now_utc = datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc)
    target_start_utc = now_utc + timedelta(hours=12)

    validate_min_hours_before_start(
        now_utc=now_utc,
        target_start_utc=target_start_utc,
        min_hours=12,
    )


def test_validate_min_hours_before_start_rejects_less_than_boundary() -> None:
    now_utc = datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc)
    target_start_utc = now_utc + timedelta(hours=11, minutes=59)

    with pytest.raises(ValueError, match="не менее 12 ч"):
        validate_min_hours_before_start(
            now_utc=now_utc,
            target_start_utc=target_start_utc,
            min_hours=12,
        )
