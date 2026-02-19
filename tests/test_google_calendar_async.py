import os
import uuid
from datetime import datetime, timezone

import pytest

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from services import google_calendar
from services import google_oauth


class _CreateEventResponse:
    status_code = 201

    def json(self):
        return {"id": "evt-1"}


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




class _DummySessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_ensure_calendar_watch_creates_state_with_channel_payload(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        def __init__(self):
            self.sync_state = None
            self.committed = 0

        async def get(self, model, key):
            return self.sync_state

        def add(self, obj):
            self.sync_state = obj

        async def commit(self):
            self.committed += 1

    class _Response:
        status_code = 200

        def json(self):
            return {"resourceId": "resource-1", "expiration": "4102444800000"}

    session = Session()

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def fake_request(_request_callable, _url, *, method_name, timeout=10, **kwargs):
        assert method_name == "POST"
        assert kwargs["json"]["type"] == "web_hook"
        assert kwargs["json"]["address"].endswith("/integrations/google-calendar/webhook")
        return _Response()

    monkeypatch.setattr(google_calendar, "async_session_factory", lambda: _DummySessionCtx(session))
    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_request)

    await google_calendar.ensure_calendar_watch(specialist_id, "cal-1")

    assert session.sync_state is not None
    assert session.sync_state.channel_id
    assert session.sync_state.resource_id == "resource-1"
    assert session.sync_state.channel_expiration is not None
    assert session.sync_state.error_count == 0
    assert session.committed == 1


@pytest.mark.asyncio
async def test_calendar_request_retries_transient_then_succeeds(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def flaky_get(url, timeout=None, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            return DummyResponse(503)
        return DummyResponse(200)

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr(google_calendar.random, "uniform", lambda *_args, **_kwargs: 0.0)
    monkeypatch.setattr(google_calendar.asyncio, "sleep", fake_sleep)

    response = await google_calendar._calendar_request_with_retry(
        flaky_get,
        "https://example.test",
        method_name="GET",
    )

    assert response.status_code == 200
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_calendar_request_does_not_retry_4xx(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        status_code = 404

    def not_found_get(url, timeout=None, **kwargs):
        calls["count"] += 1
        return DummyResponse()

    async def fail_sleep(_delay):
        raise AssertionError("sleep should not be called for 4xx")

    monkeypatch.setattr(google_calendar.asyncio, "sleep", fail_sleep)

    response = await google_calendar._calendar_request_with_retry(
        not_found_get,
        "https://example.test",
        method_name="GET",
    )

    assert response.status_code == 404
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_calendar_request_raises_after_retry_exhausted(monkeypatch):
    calls = {"count": 0}

    def always_fails(url, timeout=None, **kwargs):
        calls["count"] += 1
        raise google_calendar.requests.ConnectionError("temporary network issue")

    async def fake_sleep(_delay):
        return None

    monkeypatch.setattr(google_calendar.random, "uniform", lambda *_args, **_kwargs: 0.0)
    monkeypatch.setattr(google_calendar.asyncio, "sleep", fake_sleep)

    with pytest.raises(google_calendar.GoogleCalendarError, match="network error"):
        await google_calendar._calendar_request_with_retry(
            always_fails,
            "https://example.test",
            method_name="GET",
        )

    assert calls["count"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "display_name",
        "tg_username",
        "tg_user_id",
        "client_code",
        "expected_summary",
        "expected_description",
    ),
    [
        (
            "Анна",
            "anna",
            42,
            None,
            "Сессия с Анна (@anna)",
            "Создано автоматически после подтверждения записи в боте\n"
            "Клиент: Анна\n"
            "Telegram: @anna\n"
            "Link: https://t.me/anna",
        ),
        (
            None,
            None,
            None,
            None,
            "Сессия с Клиент",
            "Создано автоматически после подтверждения записи в боте\n"
            "Клиент: Клиент",
        ),
        (
            "Анна",
            "@anna",
            42,
            None,
            "Сессия с Анна (@anna)",
            "Создано автоматически после подтверждения записи в боте\n"
            "Клиент: Анна\n"
            "Telegram: @anna\n"
            "Link: https://t.me/anna",
        ),
        (
            "",
            None,
            42,
            "A-123",
            "Сессия с Клиент (#A-123)",
            "Создано автоматически после подтверждения записи в боте\n"
            "Клиент: Клиент\n"
            "Client code: A-123\n"
            "Telegram: tg_user_id=42\n"
            "Link: tg://user?id=42",
        ),
        (
            "Иван",
            None,
            42,
            None,
            "Сессия с Иван (tg_id=42)",
            "Создано автоматически после подтверждения записи в боте\n"
            "Клиент: Иван\n"
            "Telegram: tg_user_id=42\n"
            "Link: tg://user?id=42",
        ),
    ],
)
async def test_create_appointment_event_formats_summary_and_description(
    monkeypatch,
    display_name,
    tg_username,
    tg_user_id,
    client_code,
    expected_summary,
    expected_description,
):
    specialist_id = uuid.uuid4()
    captured_payload = {}

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def fake_calendar_request(_request_callable, _url, **kwargs):
        captured_payload.update(kwargs.get("json") or {})
        return _CreateEventResponse()

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_calendar_request)

    event = await google_calendar.create_appointment_event(
        appointment_id=uuid.uuid4(),
        specialist_id=specialist_id,
        calendar_id="primary",
        start_at_utc=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_at_utc=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        specialist_tz="UTC",
        client_display_name=display_name,
        client_tg_username=tg_username,
        client_tg_user_id=tg_user_id,
        client_code=client_code,
    )

    assert event == {"id": "evt-1"}
    assert captured_payload["summary"] == expected_summary
    assert captured_payload["description"] == expected_description
    if tg_username:
        assert "@@" not in captured_payload["summary"]
        assert "@@" not in captured_payload["description"]


async def _create_appointment_event_and_capture_payload(
    monkeypatch,
    *,
    display_name,
    username,
    tg_user_id,
    client_code,
):
    specialist_id = uuid.uuid4()
    captured_payload = {}

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def fake_calendar_request(_request_callable, _url, **kwargs):
        captured_payload.update(kwargs.get("json") or {})
        return _CreateEventResponse()

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_calendar_request)

    await google_calendar.create_appointment_event(
        appointment_id=uuid.uuid4(),
        specialist_id=specialist_id,
        calendar_id="primary",
        start_at_utc=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_at_utc=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        specialist_tz="UTC",
        client_display_name=display_name,
        client_tg_username=username,
        client_tg_user_id=tg_user_id,
        client_code=client_code,
    )

    return captured_payload


@pytest.mark.asyncio
async def test_create_appointment_event_payload_when_username_present(monkeypatch):
    payload = await _create_appointment_event_and_capture_payload(
        monkeypatch,
        display_name="Клиент А",
        username="anna",
        tg_user_id=42,
        client_code="A1",
    )

    assert "(@anna)" in payload["summary"]
    assert "https://t.me/anna" in payload["description"]


@pytest.mark.asyncio
async def test_create_appointment_event_payload_when_username_absent(monkeypatch):
    payload = await _create_appointment_event_and_capture_payload(
        monkeypatch,
        display_name="Клиент А",
        username=None,
        tg_user_id=42,
        client_code="A1",
    )

    assert "(#A1)" in payload["summary"] or "(tg_id=42)" in payload["summary"]
    assert "tg_user_id=42" in payload["description"]
    assert "tg://user?id=42" in payload["description"]


@pytest.mark.asyncio
async def test_create_appointment_event_includes_private_extended_properties(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    captured_payload = {}

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer token", "Content-Type": "application/json"}

    async def fake_calendar_request(_request_callable, _url, **kwargs):
        captured_payload.update(kwargs.get("json") or {})
        return _CreateEventResponse()

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_calendar_request)

    await google_calendar.create_appointment_event(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        calendar_id="primary",
        start_at_utc=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_at_utc=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
        specialist_tz="UTC",
        client_display_name="Клиент",
    )

    assert captured_payload["extendedProperties"]["private"]["zumbot_appointment_id"] == str(appointment_id)
    assert captured_payload["extendedProperties"]["private"]["zumbot_specialist_id"] == str(specialist_id)


def test_merge_private_extended_properties_preserves_existing_keys():
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    payload = {
        "extendedProperties": {
            "private": {"existing_key": "existing_value"},
            "shared": {"k": "v"},
        }
    }

    google_calendar._merge_private_extended_properties(
        payload,
        appointment_id=appointment_id,
        specialist_id=specialist_id,
    )

    assert payload["extendedProperties"]["private"]["existing_key"] == "existing_value"
    assert payload["extendedProperties"]["private"]["zumbot_appointment_id"] == str(appointment_id)
    assert payload["extendedProperties"]["private"]["zumbot_specialist_id"] == str(specialist_id)
    assert payload["extendedProperties"]["shared"] == {"k": "v"}


def test_required_scopes_match_minimum_calendar_access():
    scopes = google_calendar.required_scopes()
    assert "https://www.googleapis.com/auth/calendar.readonly" in scopes
    assert "https://www.googleapis.com/auth/calendar.events" in scopes
    assert "https://www.googleapis.com/auth/calendar" not in scopes


def test_scopes_as_string_contains_required_scopes():
    scopes_str = google_calendar.scopes_as_string()
    assert "https://www.googleapis.com/auth/calendar.readonly" in scopes_str
    assert "https://www.googleapis.com/auth/calendar.events" in scopes_str


def test_google_oauth_scopes_match_calendar_required_scopes():
    assert google_oauth.SCOPES == google_calendar.required_scopes()
    assert "https://www.googleapis.com/auth/calendar" not in google_oauth.SCOPES
