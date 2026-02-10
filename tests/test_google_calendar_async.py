import os
import uuid

import pytest

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from services import google_calendar


@pytest.mark.asyncio
async def test_list_calendars_uses_to_thread(monkeypatch):
    specialist_id = uuid.uuid4()

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    called = {"to_thread": False, "requests_get": False}

    class DummyResponse:
        status_code = 200

        def json(self):
            return {"items": [{"id": "1"}]}

    def fake_requests_get(url, headers=None, timeout=None):
        called["requests_get"] = True
        return DummyResponse()

    async def fake_to_thread(func, *args, **kwargs):
        called["to_thread"] = True
        assert func is google_calendar.requests.get
        return func(*args, **kwargs)

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar.requests, "get", fake_requests_get)
    monkeypatch.setattr(google_calendar.asyncio, "to_thread", fake_to_thread)

    items = await google_calendar.list_calendars(specialist_id)

    assert items == [{"id": "1"}]
    assert called["to_thread"] is True
    assert called["requests_get"] is True


@pytest.mark.asyncio
async def test_create_bot_calendar_uses_to_thread(monkeypatch):
    specialist_id = uuid.uuid4()

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    called = {"to_thread": False, "requests_post": False}

    class DummyResponse:
        status_code = 201

        def json(self):
            return {"id": "cal-1"}

    def fake_requests_post(url, headers=None, json=None, timeout=None):
        called["requests_post"] = True
        return DummyResponse()

    async def fake_to_thread(func, *args, **kwargs):
        called["to_thread"] = True
        assert func is google_calendar.requests.post
        return func(*args, **kwargs)

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar.requests, "post", fake_requests_post)
    monkeypatch.setattr(google_calendar.asyncio, "to_thread", fake_to_thread)

    result = await google_calendar.create_bot_calendar(specialist_id, "Spec")

    assert result == {"id": "cal-1"}
    assert called["to_thread"] is True
    assert called["requests_post"] is True
