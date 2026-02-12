import asyncio
import types
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
    monkeypatch.setattr(alerting, "resolve_stage", AsyncMock(return_value="master_bot"))
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
    monkeypatch.setattr(alerting, "resolve_stage", AsyncMock(return_value="personal_bot"))
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
async def test_alert_contains_stage_and_user_fields(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 300)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    monkeypatch.setattr(alerting, "resolve_stage", AsyncMock(return_value="master_bot"))
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    event = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=777, username="ivanov", first_name="Ivan", last_name="Ivanov"),
        text="/start my very long message " + ("x" * 400),
    )

    await alerting.notify_exception(
        "tests.where",
        RuntimeError("boom"),
        {"bot_id": 1},
        event=event,
        data={"handler_name": "cmd_start", "fsm_state": "Onboarding:wait"},
        user_visible_text="token=1234567:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi " + ("y" * 400),
    )

    assert len(dummy.messages) == 1
    text = dummy.messages[0][1]
    assert "stage=master_bot" in text
    assert "user=@ivanov (tg_user_id=777)" in text
    assert "handler=cmd_start" in text
    assert "fsm=Onboarding:wait" in text
    assert 'inbound="' in text
    assert 'user_visible="' in text
    assert "[REDACTED]" in text


@pytest.mark.asyncio
async def test_resolve_stage_master_vs_personal(monkeypatch):
    alerting._personal_bot_cache.clear()

    monkeypatch.setattr(alerting, "_is_personal_bot_id", AsyncMock(return_value=True))
    assert await alerting.resolve_stage(100) == "personal_bot"

    monkeypatch.setattr(alerting, "_is_personal_bot_id", AsyncMock(return_value=False))
    assert await alerting.resolve_stage(200) == "master_bot"
    assert await alerting.resolve_stage(None) == "web_server"


def test_user_context_builder():
    event = types.SimpleNamespace(
        from_user=types.SimpleNamespace(id=999, username=None, first_name="Ada", last_name="Lovelace"),
        text="hello " + ("a" * 400),
    )
    data = {"handler_name": "input_handler", "fsm_state": "S1"}

    ctx = alerting.build_user_context_from_update(event, data)

    assert ctx["tg_user_id"] == 999
    assert ctx["user_handle"] == "tg://user?id=999"
    assert ctx["user_name"] == "Ada Lovelace"
    assert ctx["handler_name"] == "input_handler"
    assert ctx["fsm_state"] == "S1"
    assert len(ctx["inbound_text"]) <= 303


@pytest.mark.asyncio
async def test_dedup_not_affected_by_user_visible_text(monkeypatch):
    monkeypatch.setattr(alerting.config, "ALERTS_ENABLED", True)
    monkeypatch.setattr(alerting.config, "ALERTS_TELEGRAM_CHAT_ID", "-1001")
    monkeypatch.setattr(alerting.config, "ALERTS_DEDUP_WINDOW_SECONDS", 300)
    monkeypatch.setattr(alerting.config, "ALERTS_THROTTLE_SECONDS", 0)

    dummy = DummyBot()

    async def fake_get_alert_bot():
        return dummy

    monkeypatch.setattr(alerting, "_get_alert_bot", fake_get_alert_bot)
    monkeypatch.setattr(alerting, "resolve_stage", AsyncMock(return_value="master_bot"))
    alerting._dedup_cache.clear()
    alerting._last_sent_ts = 0.0

    exc = RuntimeError("same failure")
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123}, user_visible_text="first")
    await alerting.notify_exception("same.where", exc, {"specialist_id": 123}, user_visible_text="second")

    assert len(dummy.messages) == 1
