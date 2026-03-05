import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:test-master-token")

from services.telegram.calendar_keyboard import _format_calendar_label


def test_format_calendar_label_basic():
    assert _format_calendar_label("Alex psy", "Europe/Moscow") == "📅 Alex psy (Europe/Moscow)"


def test_format_calendar_label_timezone_fallback():
    assert _format_calendar_label("Alex psy", None) == "📅 Alex psy (UTC)"


def test_format_calendar_label_trims_and_collapses_spaces():
    assert _format_calendar_label("  Alex   psy  ", "  Europe/Moscow  ") == "📅 Alex psy (Europe/Moscow)"


def test_format_calendar_label_truncates_long_name():
    label = _format_calendar_label("A" * 200, "Europe/Moscow")
    assert label.startswith("📅 ")
    assert "(Europe/Moscow)" in label
    assert "…" in label
