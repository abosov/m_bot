from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


_POLICY_ERROR = (
    "Запись и изменение доступны только на следующий день и только до 21:00 "
    "предыдущего дня по времени специалиста."
)


def validate_next_day_cutoff(
    *,
    specialist_tz: str,
    now_utc: datetime,
    target_start_utc: datetime,
    cutoff_hour_local: int = 21,
) -> None:
    """
    Разрешает запись/перенос только на следующий календарный день
    относительно локальной даты специалиста, и только если текущее локальное
    время <= cutoff_hour_local:00 предыдущего дня.
    Иначе raise ValueError с понятным сообщением.
    """
    tz = ZoneInfo(specialist_tz)
    now_local = now_utc.astimezone(tz)
    target_local = target_start_utc.astimezone(tz)

    is_next_day = target_local.date() == (now_local.date() + timedelta(days=1))
    if not is_next_day:
        raise ValueError(_POLICY_ERROR)

    cutoff_time = now_local.replace(
        hour=cutoff_hour_local,
        minute=0,
        second=0,
        microsecond=0,
    ).timetz().replace(tzinfo=None)
    if now_local.timetz().replace(tzinfo=None) > cutoff_time:
        raise ValueError(_POLICY_ERROR)
