from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


_POLICY_ERROR = (
    "Запись и изменение доступны только на следующий день и только до 21:00 "
    "предыдущего дня по времени специалиста."
)


def earliest_allowed_booking_date(*, specialist_tz: str, now_utc: datetime, cutoff_hour_local: int = 21):
    """Возвращает минимальную локальную дату для показа/выбора слотов по next-day+cutoff."""
    tz = ZoneInfo(specialist_tz)
    now_local = now_utc.astimezone(tz)
    min_date = now_local.date() + timedelta(days=1)

    cutoff_time = now_local.replace(
        hour=cutoff_hour_local,
        minute=0,
        second=0,
        microsecond=0,
    ).timetz().replace(tzinfo=None)
    if now_local.timetz().replace(tzinfo=None) > cutoff_time:
        min_date += timedelta(days=1)

    return min_date


def validate_next_day_cutoff(
    *,
    specialist_tz: str,
    now_utc: datetime,
    target_start_utc: datetime,
    cutoff_hour_local: int = 21,
) -> None:
    """
    Разрешает запись/перенос только на ближайшую допустимую дату:
    - до cutoff это следующий календарный день;
    - после cutoff это послезавтра.
    Иначе raise ValueError с понятным сообщением.
    """
    tz = ZoneInfo(specialist_tz)
    target_local = target_start_utc.astimezone(tz)

    min_date = earliest_allowed_booking_date(
        specialist_tz=specialist_tz,
        now_utc=now_utc,
        cutoff_hour_local=cutoff_hour_local,
    )
    if target_local.date() != min_date:
        raise ValueError(_POLICY_ERROR)
