from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.session_datetime import format_session_datetime


def test_format_session_datetime_strict_format_and_weekday() -> None:
    dt = datetime(2026, 2, 18, 10, 45, tzinfo=timezone.utc)

    formatted = format_session_datetime(dt, ZoneInfo("UTC"))

    assert formatted == "2026-02-18 Ср [10:45]"


def test_format_session_datetime_applies_timezone_conversion() -> None:
    dt = datetime(2026, 2, 18, 10, 45, tzinfo=timezone.utc)

    formatted = format_session_datetime(dt, ZoneInfo("Asia/Yekaterinburg"))

    assert formatted == "2026-02-18 Ср [15:45]"
