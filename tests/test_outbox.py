import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from database import Client, OutboxEvent, SpecialistProfile
from services import outbox
from services import outbox_notifications


class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return DummyScalarRows(self._rows)


def test_register_outbox_handlers_includes_appointment_booked():
    handlers = {}

    outbox_notifications.register_outbox_handlers(handlers)

    assert handlers["appointment_booked"] is outbox_notifications._handle_appointment_booked


@pytest.mark.asyncio
async def test_emit_domain_event_writes_row():
    added = []

    class Session:
        def add(self, obj):
            added.append(obj)

    session = Session()
    payload = {"key": "value"}

    event = await outbox.emit_domain_event(session, "test.event", payload)

    assert len(added) == 1
    assert added[0] is event
    assert event.event_type == "test.event"
    assert event.payload_json == payload


@pytest.mark.asyncio
async def test_process_outbox_events_marks_processed_at(monkeypatch):
    outbox_event = outbox.OutboxEvent(
        id=uuid.uuid4(),
        event_type="test.event",
        payload_json={"x": 1},
    )

    class Session:
        committed = False

        async def execute(self, _query):
            return DummyResult([outbox_event])

        async def commit(self):
            self.committed = True

    async def handler(_session, _outbox_event):
        return None

    session = Session()
    monkeypatch.setattr(outbox, "async_session_factory", lambda: DummySessionCtx(session))
    monkeypatch.setitem(outbox.OUTBOX_EVENT_HANDLERS, "test.event", handler)

    processed_count = await outbox.process_outbox_events(limit=50)

    assert processed_count == 1
    assert outbox_event.processed_at is not None
    assert isinstance(outbox_event.processed_at, datetime)
    assert outbox_event.processed_at.tzinfo == timezone.utc
    assert outbox_event.error is None
    assert session.committed is True




@pytest.mark.asyncio
async def test_process_outbox_events_marks_missing_handler_as_processed(monkeypatch):
    outbox_event = outbox.OutboxEvent(
        id=uuid.uuid4(),
        event_type="unknown.event",
        payload_json={},
    )

    class Session:
        committed = False

        async def execute(self, _query):
            return DummyResult([outbox_event])

        async def commit(self):
            self.committed = True

    session = Session()
    monkeypatch.setattr(outbox, "async_session_factory", lambda: DummySessionCtx(session))

    processed_count = await outbox.process_outbox_events(limit=50)

    assert processed_count == 1
    assert outbox_event.processed_at is not None
    assert outbox_event.error == "handler_missing"
    assert outbox_event.attempts is None
    assert session.committed is True

@pytest.mark.asyncio
async def test_process_outbox_events_invokes_registered_handler(monkeypatch):
    event = OutboxEvent(id=uuid.uuid4(), event_type="x.test", payload_json={})
    calls = []

    class Session:
        async def execute(self, _query):
            return DummyResult([event])

        async def commit(self):
            return None

    async def handler(session, outbox_event):
        calls.append((session, outbox_event.id))

    session = Session()
    monkeypatch.setattr(outbox, "async_session_factory", lambda: DummySessionCtx(session))
    monkeypatch.setitem(outbox.OUTBOX_EVENT_HANDLERS, "x.test", handler)

    await outbox.process_outbox_events()

    assert calls == [(session, event.id)]


@pytest.mark.asyncio
async def test_rescheduled_handler_sends_client_and_specialist(monkeypatch):
    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_type="appointment_rescheduled",
        payload_json={
            "appointment_id": str(appointment_id),
            "specialist_id": str(specialist_id),
            "client_id": str(client_id),
            "old_start_at_utc": "2026-01-02T10:00:00+00:00",
            "new_start_at_utc": "2026-01-02T11:00:00+00:00",
        },
    )

    client = Client(
        client_id=client_id,
        specialist_id=specialist_id,
        tg_user_id=111,
        client_code="C-1",
        client_timezone="UTC",
        timezone_source="default_from_specialist",
    )
    specialist = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="sp",
        owner_tg_user_id=222,
        specialist_timezone="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=4,
        slot_step_min=30,
        cancel_window_hours=12,
    )

    class Session:
        async def get(self, model, key):
            if model is Client and key == client_id:
                return client
            if model is SpecialistProfile and key == specialist_id:
                return specialist
            return None

    sent = []

    async def fake_send_client_message(_session, **kwargs):
        sent.append(("client", kwargs["client"].tg_user_id, kwargs["text"]))

    async def fake_send_specialist_message(_session, **kwargs):
        sent.append(("specialist", kwargs["specialist_tg_user_id"], kwargs["text"]))

    async def fake_load_personal_bot(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(outbox_notifications, "_load_personal_bot", fake_load_personal_bot)
    monkeypatch.setattr(outbox_notifications, "_send_client_message", fake_send_client_message)
    monkeypatch.setattr(outbox_notifications, "_send_specialist_message", fake_send_specialist_message)

    await outbox_notifications._handle_appointment_rescheduled(Session(), event)

    assert len(sent) == 2
    assert sent[0][0] == "client"
    assert "Было: 2026-01-02 Пт [10:00]" in sent[0][2]
    assert "Стало: 2026-01-02 Пт [11:00]" in sent[0][2]
    assert "записи #" not in sent[0][2]
    assert sent[1][0] == "specialist"
    assert "Новое время: 2026-01-02 Пт [11:00]" in sent[1][2]
    assert "Перенос записи выполнен." in sent[1][2]
    assert "записи #" not in sent[1][2]


@pytest.mark.asyncio
async def test_cancelled_handler_requires_client_id():
    event = OutboxEvent(
        id=uuid.uuid4(),
        event_type="appointment_cancelled_by_specialist_calendar",
        payload_json={
            "appointment_id": str(uuid.uuid4()),
            "specialist_id": str(uuid.uuid4()),
        },
    )

    class Session:
        async def get(self, _model, _key):
            return None

    with pytest.raises(ValueError, match="client_id"):
        await outbox_notifications._handle_appointment_cancelled_by_specialist_calendar(Session(), event)


@pytest.mark.asyncio
async def test_cancelled_by_client_handler_sends_specialist_without_appointment_id(monkeypatch):
    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_type="appointment_cancelled_by_client",
        payload_json={
            "appointment_id": str(appointment_id),
            "specialist_id": str(specialist_id),
            "client_id": str(client_id),
            "start_at_utc": "2026-01-02T11:00:00+00:00",
        },
    )

    client = Client(
        client_id=client_id,
        specialist_id=specialist_id,
        tg_user_id=111,
        client_code="C-1",
        client_timezone="UTC",
        timezone_source="default_from_specialist",
    )
    specialist = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="sp",
        owner_tg_user_id=222,
        specialist_timezone="Europe/Moscow",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=4,
        slot_step_min=30,
        cancel_window_hours=12,
    )

    class Session:
        async def get(self, model, key):
            if model is Client and key == client_id:
                return client
            if model is SpecialistProfile and key == specialist_id:
                return specialist
            return None

    sent = []

    async def fake_send_specialist_message(_session, **kwargs):
        sent.append((kwargs["specialist_tg_user_id"], kwargs["text"]))

    async def fake_load_personal_bot(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(outbox_notifications, "_load_personal_bot", fake_load_personal_bot)
    monkeypatch.setattr(outbox_notifications, "_send_specialist_message", fake_send_specialist_message)

    await outbox_notifications._handle_appointment_cancelled_by_client(Session(), event)

    assert sent[0][0] == 222
    assert "Клиент отменил запись." in sent[0][1]
    assert "Время: 2026-01-02 Пт [14:00]" in sent[0][1]
    assert "записи #" not in sent[0][1]
    assert str(appointment_id) not in sent[0][1]


@pytest.mark.asyncio
async def test_booked_handler_sends_specialist_with_username_link(monkeypatch):
    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_type="appointment_booked",
        payload_json={
            "appointment_id": str(appointment_id),
            "specialist_id": str(specialist_id),
            "client_id": str(client_id),
            "start_at_utc": "2026-01-02T11:00:00+00:00",
        },
    )

    client = Client(
        client_id=client_id,
        specialist_id=specialist_id,
        tg_user_id=111,
        tg_username="smoke_client",
        display_name="Smoke Client",
        client_code="C-1",
        client_timezone="UTC",
        timezone_source="default_from_specialist",
    )
    specialist = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="sp",
        owner_tg_user_id=222,
        specialist_timezone="Europe/Moscow",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=4,
        slot_step_min=30,
        cancel_window_hours=12,
    )

    class Session:
        async def get(self, model, key):
            if model is Client and key == client_id:
                return client
            if model is SpecialistProfile and key == specialist_id:
                return specialist
            return None

    sent = []

    async def fake_send_specialist_message(_session, **kwargs):
        sent.append((kwargs["specialist_tg_user_id"], kwargs["text"]))

    async def fake_load_personal_bot(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(outbox_notifications, "_load_personal_bot", fake_load_personal_bot)
    monkeypatch.setattr(outbox_notifications, "_send_specialist_message", fake_send_specialist_message)

    await outbox_notifications._handle_appointment_booked(Session(), event)

    assert len(sent) == 1
    assert sent[0][0] == 222
    assert "Новая запись: 2026-01-02 Пт [14:00]" in sent[0][1]
    assert "@smoke_client" in sent[0][1]
    assert "https://t.me/smoke_client" in sent[0][1]
    assert "appointment_id" not in sent[0][1]
    assert str(appointment_id) not in sent[0][1]


@pytest.mark.asyncio
async def test_booked_handler_sends_specialist_with_deeplink_when_no_username(monkeypatch):
    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    event = OutboxEvent(
        id=uuid.uuid4(),
        event_type="appointment_booked",
        payload_json={
            "appointment_id": str(appointment_id),
            "specialist_id": str(specialist_id),
            "client_id": str(client_id),
            "start_at_utc": "2026-01-02T11:00:00+00:00",
        },
    )

    client = Client(
        client_id=client_id,
        specialist_id=specialist_id,
        tg_user_id=123456789,
        tg_username=None,
        display_name="Smoke Client",
        client_code="C-1",
        client_timezone="UTC",
        timezone_source="default_from_specialist",
    )
    specialist = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="sp",
        owner_tg_user_id=222,
        specialist_timezone="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=4,
        slot_step_min=30,
        cancel_window_hours=12,
    )

    class Session:
        async def get(self, model, key):
            if model is Client and key == client_id:
                return client
            if model is SpecialistProfile and key == specialist_id:
                return specialist
            return None

    sent = []

    async def fake_send_specialist_message(_session, **kwargs):
        sent.append((kwargs["specialist_tg_user_id"], kwargs["text"]))

    async def fake_load_personal_bot(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(outbox_notifications, "_load_personal_bot", fake_load_personal_bot)
    monkeypatch.setattr(outbox_notifications, "_send_specialist_message", fake_send_specialist_message)

    await outbox_notifications._handle_appointment_booked(Session(), event)

    assert len(sent) == 1
    assert sent[0][0] == 222
    assert "Новая запись: 2026-01-02 Пт [11:00]" in sent[0][1]
    assert "Smoke Client" in sent[0][1]
    assert "tg://user?id=123456789" in sent[0][1]
    assert "appointment_id" not in sent[0][1]
    assert str(appointment_id) not in sent[0][1]
