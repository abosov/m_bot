import os
import uuid

import pytest

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from services import google_calendar


class FakeResponse:
    status_code = 200

    def json(self):
        return {"timeZone": "Europe/Berlin"}


@pytest.mark.asyncio
async def test_resolve_tz_uses_primary_when_profile_tz_none(monkeypatch):
    specialist_id = uuid.uuid4()

    async def fake_build_headers(_specialist_id):
        return {"Authorization": "Bearer fake"}

    def fake_get(url, timeout=None, **kwargs):
        return FakeResponse()

    async def fake_retry(request_callable, url, **kwargs):
        return request_callable(url, **kwargs)

    monkeypatch.setattr(google_calendar, "_build_headers", fake_build_headers)
    monkeypatch.setattr(google_calendar.requests, "get", fake_get)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_retry)

    tz = await google_calendar.resolve_tz_for_calendar_creation(specialist_id=specialist_id, profile_tz=None)

    assert tz == "Europe/Berlin"


@pytest.mark.asyncio
async def test_resolve_tz_uses_primary_when_profile_tz_utc(monkeypatch):
    specialist_id = uuid.uuid4()

    async def fake_build_headers(_specialist_id):
        return {"Authorization": "Bearer fake"}

    def fake_get(url, timeout=None, **kwargs):
        return FakeResponse()

    async def fake_retry(request_callable, url, **kwargs):
        return request_callable(url, **kwargs)

    monkeypatch.setattr(google_calendar, "_build_headers", fake_build_headers)
    monkeypatch.setattr(google_calendar.requests, "get", fake_get)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_retry)

    tz = await google_calendar.resolve_tz_for_calendar_creation(specialist_id=specialist_id, profile_tz="UTC")

    assert tz == "Europe/Berlin"


@pytest.mark.asyncio
async def test_resolve_tz_keeps_non_utc_profile_and_skips_primary_call(monkeypatch):
    specialist_id = uuid.uuid4()
    calls = {"count": 0}

    async def fake_get_primary(_specialist_id):
        calls["count"] += 1
        return "Europe/Berlin"

    monkeypatch.setattr(google_calendar, "get_primary_calendar_timezone", fake_get_primary)

    tz = await google_calendar.resolve_tz_for_calendar_creation(
        specialist_id=specialist_id,
        profile_tz="Asia/Tokyo",
    )

    assert tz == "Asia/Tokyo"
    assert calls["count"] == 0
