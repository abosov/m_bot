import os
import uuid
from datetime import datetime, timezone

import pytest

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from database import CalendarSyncState
from services import google_calendar
from services import google_calendar_reverse_sync


class _DummySessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_reverse_sync_sync_token_invalid_falls_back_to_full_sync(monkeypatch):
    specialist_id = uuid.uuid4()
    calendar_id = "primary"

    class Session:
        def __init__(self):
            self.sync_state = CalendarSyncState(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                sync_token="stale-token",
                error_count=0,
            )
            self.links = {}
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == "CalendarSyncState":
                return self.sync_state
            if model.__name__ == "AppointmentCalendarLink":
                return self.links.get(key)
            return None

        def add(self, obj):
            return None

        async def commit(self):
            self.committed = True

    session = Session()
    call_params = []

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer x"}

    async def fake_request(_request_callable, _url, *, method_name, timeout=10, **kwargs):
        assert method_name == "GET"
        call_params.append(kwargs["params"])
        if kwargs["params"].get("syncToken") == "stale-token":
            return _Response(410, {"error": {"message": "Sync token is no longer valid"}})
        return _Response(
            200,
            {
                "items": [],
                "nextSyncToken": "fresh-token",
            },
        )

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_request)
    monkeypatch.setattr(google_calendar_reverse_sync, "async_session_factory", lambda: _DummySessionCtx(session))

    await google_calendar_reverse_sync.run_calendar_reverse_sync(specialist_id, calendar_id)

    assert len(call_params) == 2
    assert call_params[0].get("syncToken") == "stale-token"
    assert "syncToken" not in call_params[1]
    assert session.sync_state.sync_token == "fresh-token"
    assert session.committed is True


@pytest.mark.asyncio
async def test_reverse_sync_ignores_events_without_zumbot_appointment_id(monkeypatch):
    specialist_id = uuid.uuid4()
    calendar_id = "primary"

    class Session:
        def __init__(self):
            self.sync_state = CalendarSyncState(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                sync_token=None,
                error_count=0,
            )
            self.links = {}
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == "CalendarSyncState":
                return self.sync_state
            if model.__name__ == "AppointmentCalendarLink":
                return self.links.get(key)
            return None

        def add(self, obj):
            return None

        async def commit(self):
            self.committed = True

    session = Session()
    reconcile_called = {"count": 0}

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer x"}

    async def fake_request(_request_callable, _url, *, method_name, timeout=10, **kwargs):
        assert method_name == "GET"
        return _Response(
            200,
            {
                "items": [
                    {
                        "id": "evt-1",
                        "etag": '"etag-1"',
                        "updated": datetime.now(timezone.utc).isoformat(),
                        "extendedProperties": {"private": {}},
                    }
                ],
                "nextSyncToken": "sync-2",
            },
        )

    async def fake_reconcile(event, _specialist_id, _calendar_id):
        reconcile_called["count"] += 1

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_request)
    monkeypatch.setattr(google_calendar_reverse_sync, "reconcile_event_to_appointment", fake_reconcile)
    monkeypatch.setattr(google_calendar_reverse_sync, "async_session_factory", lambda: _DummySessionCtx(session))

    await google_calendar_reverse_sync.run_calendar_reverse_sync(specialist_id, calendar_id)

    assert reconcile_called["count"] == 0
    assert session.sync_state.sync_token == "sync-2"
    assert session.committed is True
