import os

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from fastapi.testclient import TestClient

import web_server


class DummySession:
    async def close(self):
        return None


class DummyBot:
    def __init__(self):
        self.session = DummySession()


def test_lifespan_shutdown_closes_personal_cache_and_master_session(monkeypatch):
    calls = []

    async def fake_close_personal_bot_cache():
        calls.append("personal")

    dummy_bot = DummyBot()

    async def fake_master_close():
        calls.append("master")

    monkeypatch.setattr(web_server, "close_personal_bot_cache", fake_close_personal_bot_cache)
    monkeypatch.setattr(dummy_bot.session, "close", fake_master_close)
    monkeypatch.setattr(web_server, "bot", dummy_bot)

    with TestClient(web_server.app):
        pass

    assert calls == ["personal", "master"]
