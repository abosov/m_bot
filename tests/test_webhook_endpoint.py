import os

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

import types
import uuid

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
