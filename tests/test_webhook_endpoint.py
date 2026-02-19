import os

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

import types
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import web_server
from database import TelegramBotStatus


class Result:
    def __init__(self, bot):
        self.bot = bot

    def scalar_one_or_none(self):
        return self.bot

class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_personal_webhook_returns_200_and_processes_update(monkeypatch):
    captured = {}

    class Session:
        async def execute(self, stmt):
            bot = types.SimpleNamespace(
                bot_user_id=123,
                specialist_id=uuid.uuid4(),
                webhook_secret="secret",
                status=TelegramBotStatus.active,
            )
            return Result(bot)

    async def fake_process_update(bot, raw_update):
        captured["bot_id"] = bot.bot_user_id
        captured["update_id"] = raw_update["update_id"]

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "process_update", fake_process_update)

    client = TestClient(web_server.app)
    response = client.post(
        "/tg/webhook/123/secret",
        json={"update_id": 1, "message": {"message_id": 1, "date": 1, "chat": {"id": 1, "type": "private"}, "text": "/start"}},
    )

    assert response.status_code == 200
    assert captured == {"bot_id": 123, "update_id": 1}


def test_personal_webhook_returns_404_for_invalid_secret(monkeypatch):
    class Session:
        async def execute(self, stmt):
            return Result(None)

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))

    client = TestClient(web_server.app)
    response = client.post("/tg/webhook/123/wrong", json={"update_id": 1})

    assert response.status_code == 404


def test_personal_webhook_returns_413_for_oversized_payload(monkeypatch):
    called = {"value": False}

    class Session:
        async def execute(self, stmt):
            bot = types.SimpleNamespace(
                bot_user_id=123,
                specialist_id=uuid.uuid4(),
                webhook_secret="secret",
                status=TelegramBotStatus.active,
            )
            return Result(bot)

    async def fake_process_update(bot, raw_update):
        called["value"] = True

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "process_update", fake_process_update)
    monkeypatch.setattr(web_server, "MAX_WEBHOOK_BODY_BYTES", 200)

    client = TestClient(web_server.app)
    body = "x" * 300
    response = client.post(
        "/tg/webhook/123/secret",
        data=body,
        headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "payload_too_large"}
    assert called["value"] is False


def test_personal_webhook_logs_without_secret(monkeypatch, caplog):
    class Session:
        async def execute(self, stmt):
            bot = types.SimpleNamespace(
                bot_user_id=123,
                specialist_id=uuid.uuid4(),
                webhook_secret="super-secret-value",
                status=TelegramBotStatus.active,
            )
            return Result(bot)

    async def fake_process_update(bot, raw_update):
        return None

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "process_update", fake_process_update)

    client = TestClient(web_server.app)
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/tg/webhook/123/super-secret-value",
            json={"update_id": 1, "message": {"message_id": 1}},
        )

    assert response.status_code == 200
    webhook_logs = [record.getMessage() for record in caplog.records if record.name == "web_server"]
    assert webhook_logs
    logs = "\n".join(webhook_logs)
    assert "super-secret-value" not in logs


def test_request_id_header_and_log_present(monkeypatch, caplog):
    class Session:
        async def execute(self, stmt):
            bot = types.SimpleNamespace(
                bot_user_id=123,
                specialist_id=uuid.uuid4(),
                webhook_secret="secret",
                status=TelegramBotStatus.active,
            )
            return Result(bot)

    async def fake_process_update(bot, raw_update):
        return None

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "process_update", fake_process_update)

    client = TestClient(web_server.app)
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/tg/webhook/123/secret",
            json={"update_id": 1},
            headers={"X-Request-ID": "req-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert any("request_id=req-123" in record.getMessage() for record in caplog.records)


def test_google_calendar_webhook_enqueues_reverse_sync(monkeypatch):
    captured = {}

    class Session:
        async def execute(self, stmt):
            class SyncResult:
                def first(self_nonlocal):
                    return (uuid.UUID("00000000-0000-0000-0000-000000000123"), "primary", None)

            return SyncResult()

        async def commit(self):
            return None

    async def fake_reverse_sync(specialist_id, calendar_id):
        captured["specialist_id"] = specialist_id
        captured["calendar_id"] = calendar_id

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "run_calendar_reverse_sync", fake_reverse_sync)

    client = TestClient(web_server.app)
    response = client.post(
        "/integrations/google-calendar/webhook",
        headers={
            "X-Goog-Channel-Id": "channel-1",
            "X-Goog-Resource-Id": "resource-1",
            "X-Goog-Resource-State": "exists",
            "X-Goog-Message-Number": "2",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "specialist_id": uuid.UUID("00000000-0000-0000-0000-000000000123"),
        "calendar_id": "primary",
    }




def test_google_calendar_webhook_skips_reverse_sync_within_throttle_window(monkeypatch, caplog):
    called = {"value": False}

    class Session:
        def __init__(self):
            self.committed = False

        async def execute(self, stmt):
            class SyncResult:
                def first(self_nonlocal):
                    return (
                        uuid.UUID("00000000-0000-0000-0000-000000000123"),
                        "primary",
                        datetime.now(timezone.utc) - timedelta(seconds=5),
                    )

            return SyncResult()

        async def commit(self):
            self.committed = True

    async def fake_reverse_sync(specialist_id, calendar_id):
        called["value"] = True

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "run_calendar_reverse_sync", fake_reverse_sync)

    client = TestClient(web_server.app)
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/integrations/google-calendar/webhook",
            headers={
                "X-Goog-Channel-Id": "channel-1",
                "X-Goog-Resource-Id": "resource-1",
                "X-Goog-Resource-State": "exists",
                "X-Goog-Message-Number": "3",
            },
        )

    assert response.status_code == 200
    assert called["value"] is False
    assert any("reverse_sync_skipped_throttle" in record.getMessage() for record in caplog.records)


def test_google_calendar_webhook_returns_200_without_required_headers(monkeypatch, caplog):
    called = {"value": False}

    async def fake_reverse_sync(specialist_id, calendar_id):
        called["value"] = True

    monkeypatch.setattr(web_server, "run_calendar_reverse_sync", fake_reverse_sync)

    client = TestClient(web_server.app)
    with caplog.at_level(logging.WARNING):
        response = client.post("/integrations/google-calendar/webhook")

    assert response.status_code == 200
    assert called["value"] is False
    assert any("google_calendar_webhook_missing_headers" in record.getMessage() for record in caplog.records)


def test_google_calendar_webhook_returns_200_for_unknown_channel(monkeypatch, caplog):
    called = {"value": False}

    class Session:
        async def execute(self, stmt):
            class SyncResult:
                def first(self_nonlocal):
                    return None

            return SyncResult()

    async def fake_reverse_sync(specialist_id, calendar_id):
        called["value"] = True

    monkeypatch.setattr(web_server, "async_session_factory", lambda: DummySessionCtx(Session()))
    monkeypatch.setattr(web_server, "run_calendar_reverse_sync", fake_reverse_sync)

    client = TestClient(web_server.app)
    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/integrations/google-calendar/webhook",
            headers={
                "X-Goog-Channel-Id": "missing-channel",
                "X-Goog-Resource-Id": "resource-1",
                "X-Goog-Resource-State": "exists",
            },
        )

    assert response.status_code == 200
    assert called["value"] is False
    assert any("google_calendar_webhook_unknown_channel" in record.getMessage() for record in caplog.records)
