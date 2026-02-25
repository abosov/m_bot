import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from database import Appointment, BookingState, CalendarSyncState, OutboxEvent
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


@pytest.mark.asyncio
async def test_reverse_sync_rejected_appointment_not_found_does_not_create_link(monkeypatch):
    specialist_id = uuid.uuid4()
    calendar_id = "primary"
    missing_appointment_id = uuid.uuid4()

    class Session:
        def __init__(self):
            self.sync_state = CalendarSyncState(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                sync_token=None,
                error_count=0,
            )
            self.links = {}
            self.added = []
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == "CalendarSyncState":
                return self.sync_state
            if model.__name__ == "AppointmentCalendarLink":
                return self.links.get(key)
            return None

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.committed = True

    session = Session()

    async def fake_headers(_specialist_id):
        return {"Authorization": "Bearer x"}

    async def fake_request(_request_callable, _url, *, method_name, timeout=10, **kwargs):
        assert method_name == "GET"
        return _Response(
            200,
            {
                "items": [
                    {
                        "id": "evt-missing-appointment",
                        "etag": '"etag-1"',
                        "updated": datetime.now(timezone.utc).isoformat(),
                        "extendedProperties": {
                            "private": {
                                "zumbot_managed": "1",
                                "zumbot_appointment_id": str(missing_appointment_id),
                            }
                        },
                    }
                ],
                "nextSyncToken": "sync-2",
            },
        )

    monkeypatch.setattr(google_calendar, "_build_headers", fake_headers)
    monkeypatch.setattr(google_calendar, "_calendar_request_with_retry", fake_request)
    monkeypatch.setattr(google_calendar_reverse_sync, "async_session_factory", lambda: _DummySessionCtx(session))

    await google_calendar_reverse_sync.run_calendar_reverse_sync(specialist_id, calendar_id)

    assert session.sync_state.sync_token == "sync-2"
    assert session.committed is True
    assert session.added == []


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_reconcile_event_reschedules_when_notice_is_enough(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=now + timedelta(hours=30),
        end_at_utc=now + timedelta(hours=31),
        booking_state=BookingState.confirmed,
        idempotency_key='k-1',
    )

    class Session:
        def __init__(self):
            self.committed = False
            self.added = []

        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(None)

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.committed = True

    session = Session()

    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-1',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
        'start': {'dateTime': (now + timedelta(hours=40)).isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (now + timedelta(hours=41)).isoformat(), 'timeZone': 'UTC'},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.UPDATED
    assert appointment.start_at_utc == datetime.fromisoformat(event['start']['dateTime']).astimezone(timezone.utc)
    assert appointment.end_at_utc == datetime.fromisoformat(event['end']['dateTime']).astimezone(timezone.utc)
    assert session.committed is True
    outbox_events = [obj for obj in session.added if isinstance(obj, OutboxEvent)]
    assert len(outbox_events) == 1
    assert outbox_events[0].event_type == 'appointment_rescheduled'
    payload = outbox_events[0].payload_json
    assert payload['appointment_id'] == str(appointment_id)
    assert payload['specialist_id'] == str(specialist_id)
    assert payload['client_id'] == str(client_id)
    assert 'old_start_at_utc' in payload
    assert 'new_start_at_utc' in payload


@pytest.mark.asyncio
async def test_reconcile_event_rejected_when_notice_too_short(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    old_start = now + timedelta(hours=2)
    old_end = now + timedelta(hours=3)
    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=old_start,
        end_at_utc=old_end,
        booking_state=BookingState.confirmed,
        idempotency_key='k-2',
    )

    class Session:
        def __init__(self):
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(None)

        async def commit(self):
            self.committed = True

    session = Session()

    async def fake_emit_outbox_domain_event(session, event_type, payload):
        raise AssertionError('must not emit for rejected reconcile')

    monkeypatch.setattr(google_calendar_reverse_sync, 'emit_outbox_domain_event', fake_emit_outbox_domain_event)
    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-2',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
        'start': {'dateTime': (now + timedelta(hours=20)).isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (now + timedelta(hours=21)).isoformat(), 'timeZone': 'UTC'},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.REJECTED
    assert result.reason == 'min_notice_violation'
    assert appointment.start_at_utc == old_start
    assert appointment.end_at_utc == old_end
    assert session.committed is False


@pytest.mark.asyncio
async def test_reconcile_event_rejected_on_time_conflict(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    old_start = now + timedelta(hours=30)
    old_end = now + timedelta(hours=31)
    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=old_start,
        end_at_utc=old_end,
        booking_state=BookingState.confirmed,
        idempotency_key='k-3',
    )

    class Session:
        def __init__(self):
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(uuid.uuid4())

        async def commit(self):
            self.committed = True

    session = Session()

    async def fake_emit_outbox_domain_event(session, event_type, payload):
        raise AssertionError('must not emit for rejected reconcile')

    monkeypatch.setattr(google_calendar_reverse_sync, 'emit_outbox_domain_event', fake_emit_outbox_domain_event)
    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-3',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
        'start': {'dateTime': (now + timedelta(hours=40)).isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (now + timedelta(hours=41)).isoformat(), 'timeZone': 'UTC'},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.REJECTED
    assert result.reason == 'time_conflict'
    assert appointment.start_at_utc == old_start
    assert appointment.end_at_utc == old_end
    assert session.committed is False


@pytest.mark.asyncio
async def test_reconcile_event_cancels_appointment_when_google_event_cancelled(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=now + timedelta(hours=30),
        end_at_utc=now + timedelta(hours=31),
        booking_state=BookingState.confirmed,
        idempotency_key='k-4',
    )

    class Session:
        def __init__(self):
            self.committed = False
            self.added = []

        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(None)

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.committed = True

    session = Session()

    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-cancel-1',
        'status': 'cancelled',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.UPDATED
    assert appointment.booking_state == BookingState.canceled_by_specialist
    assert session.committed is True
    outbox_events = [obj for obj in session.added if isinstance(obj, OutboxEvent)]
    assert len(outbox_events) == 1
    assert outbox_events[0].event_type == 'appointment_cancelled_by_specialist_calendar'
    payload = outbox_events[0].payload_json
    assert payload['appointment_id'] == str(appointment_id)
    assert payload['specialist_id'] == str(specialist_id)
    assert payload['client_id'] == str(client_id)
    assert payload['start_at_utc'] == appointment.start_at_utc.isoformat()


@pytest.mark.asyncio
async def test_reconcile_event_cancelled_noop_when_appointment_already_cancelled(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    client_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=now + timedelta(hours=30),
        end_at_utc=now + timedelta(hours=31),
        booking_state=BookingState.canceled_by_specialist,
        idempotency_key='k-5',
    )

    class Session:
        def __init__(self):
            self.committed = False

        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(None)

        async def commit(self):
            self.committed = True

    session = Session()

    async def fake_emit_outbox_domain_event(session, event_type, payload):
        raise AssertionError('must not emit for noop cancel')

    monkeypatch.setattr(google_calendar_reverse_sync, 'emit_outbox_domain_event', fake_emit_outbox_domain_event)
    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-cancel-2',
        'status': 'cancelled',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.NOOP
    assert appointment.booking_state == BookingState.canceled_by_specialist
    assert session.committed is False


@pytest.mark.asyncio
async def test_reconcile_event_rejected_for_rejected_appointment_state(monkeypatch):
    specialist_id = uuid.uuid4()
    appointment_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    appointment = Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=uuid.uuid4(),
        start_at_utc=now + timedelta(hours=30),
        end_at_utc=now + timedelta(hours=31),
        booking_state=BookingState.rejected_by_specialist,
        idempotency_key='k-rejected',
    )

    class Session:
        async def get(self, model, key):
            if model.__name__ == 'Appointment' and key == appointment_id:
                return appointment
            return None

        async def execute(self, _stmt):
            return _ScalarResult(None)

        async def commit(self):
            raise AssertionError('commit must not happen for rejected state')

    session = Session()

    async def fake_emit_outbox_domain_event(session, event_type, payload):
        raise AssertionError('must not emit for inactive booking state')

    monkeypatch.setattr(google_calendar_reverse_sync, 'emit_outbox_domain_event', fake_emit_outbox_domain_event)
    monkeypatch.setattr(google_calendar_reverse_sync, 'async_session_factory', lambda: _DummySessionCtx(session))

    event = {
        'id': 'evt-rejected',
        'extendedProperties': {'private': {'zumbot_managed': '1', 'zumbot_appointment_id': str(appointment_id)}},
        'start': {'dateTime': (now + timedelta(hours=40)).isoformat(), 'timeZone': 'UTC'},
        'end': {'dateTime': (now + timedelta(hours=41)).isoformat(), 'timeZone': 'UTC'},
    }

    result = await google_calendar_reverse_sync.reconcile_event_to_appointment(event, specialist_id, 'primary')

    assert result.result == google_calendar_reverse_sync.ReconcileOutcome.REJECTED
    assert result.reason == 'inactive_booking_state'


@pytest.mark.asyncio
async def test_reverse_sync_ignores_marked_events_without_appointment_id(monkeypatch):
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
                        "id": "evt-marked-without-appointment",
                        "etag": '"etag-1"',
                        "updated": datetime.now(timezone.utc).isoformat(),
                        "extendedProperties": {"private": {"zumbot_managed": "1"}},
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
