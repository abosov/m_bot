from __future__ import annotations

from datetime import datetime, timedelta


_POLICY_ERROR = "Операция доступна только если до начала слота осталось не менее {min_hours} ч."


def validate_min_hours_before_start(*, now_utc: datetime, target_start_utc: datetime, min_hours: int) -> None:
    """Проверяет, что до начала слота осталось не меньше min_hours часов."""
    if target_start_utc - now_utc < timedelta(hours=min_hours):
        raise ValueError(_POLICY_ERROR.format(min_hours=min_hours))
