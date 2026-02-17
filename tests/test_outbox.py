import uuid
from datetime import datetime, timezone

import pytest

from services import outbox


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

    session = Session()
    monkeypatch.setattr(outbox, "async_session_factory", lambda: DummySessionCtx(session))

    processed_count = await outbox.process_outbox_events(limit=50)

    assert processed_count == 1
    assert outbox_event.processed_at is not None
    assert isinstance(outbox_event.processed_at, datetime)
    assert outbox_event.processed_at.tzinfo == timezone.utc
    assert outbox_event.error is None
    assert session.committed is True
