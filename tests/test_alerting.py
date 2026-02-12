import asyncio
from unittest.mock import AsyncMock

import pytest

from services import alerting


class DummyBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


@pytest.mark.asyncio
async def test_sanitize_context_removes_secrets():
    context = {
        "token": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
        "refresh_token": "refresh-secret",
        "db_url": "postgres://user:pass@localhost:5432/db",
        "nested": {"client_secret": "top-secret", "ok": "value"},
    }

    sanitized = alerting.sanitize_context(context)

    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["refresh_token"] == "[REDACTED]"
    assert sanitized["db_url"] == "[REDACTED]"
    assert sanitized["nested"]["client_secret"] == "[REDACTED]"
    assert sanitized["nested"]["ok"] == "value"


@pytest.mark.asyncio
async def test_alerts_disabled_skip_send(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", False)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "1")
    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)

    await alerting.notify_exception("tests.where", RuntimeError("boom"), {})

    assert dummy.messages == []


@pytest.mark.asyncio
async def test_deduplication_suppresses_same_error(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 300)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    exc = RuntimeError("same failure")
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123})
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123})

    assert len(dummy.messages) == 1


@pytest.mark.asyncio
async def test_two_identical_errors_send_once(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 600)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    await asyncio.gather(
        alerting.notify_exception("parallel.where", ValueError("same"), {"bot_id": 5}),
        alerting.notify_exception("parallel.where", ValueError("same"), {"bot_id": 5}),
    )

    assert len(dummy.messages) == 1


@pytest.mark.asyncio
async def test_close_alerting_closes_bot_session(monkeypatch):
    session_close = AsyncMock()
    bot = type("BotStub", (), {"session": type("SessionStub", (), {"close": session_close})()})()

    monkeypatch.setattr(alerting, "_alert_bot", bot)
    monkeypatch.setattr(alerting, "_alert_bot_token", "token")

    await alerting.close_alerting()

    session_close.assert_awaited_once()
    assert alerting._alert_bot is None
    assert alerting._alert_bot_token is None


@pytest.mark.asyncio
async def test_alert_contains_stage_username_and_trimmed_user_message(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 300)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    long_user_message = "token=1234567:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi " + ("x" * 400)
    await alerting.notify_exception(
        "tests.where",
        RuntimeError("boom"),
        {},
        stage="master_onboarding",
        username="ivanov",
        user_message=long_user_message,
    )

    assert len(dummy.messages) == 1
    text = dummy.messages[0][1]
    assert "stage=master_onboarding" in text
    assert "username=@ivanov" in text
    assert "user_message=\"" in text
    assert "[REDACTED]" in text

    user_message_line = next(line for line in text.splitlines() if line.startswith("user_message="))
    assert len(user_message_line) <= 320


@pytest.mark.asyncio
async def test_deduplication_respects_stage(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 300)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    exc = RuntimeError("same failure")
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123}, stage="master_onboarding")
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123}, stage="master_onboarding")

    assert len(dummy.messages) == 1

    await alerting.notify_exception("same.where", exc, {"specialist_id": 123}, stage="webhook")

    assert len(dummy.messages) == 2
