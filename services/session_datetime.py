from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

RU_WEEKDAY_SHORT = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def format_session_datetime(dt: datetime, tz: ZoneInfo) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_dt = dt.astimezone(tz)
    weekday_short = RU_WEEKDAY_SHORT[local_dt.weekday()]
    return f"{local_dt:%Y-%m-%d} {weekday_short} [{local_dt:%H:%M}]"
