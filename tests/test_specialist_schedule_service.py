from __future__ import annotations

import uuid
from datetime import time

import pytest

from services import specialist_schedule


class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class DummyScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_get_specialist_schedule_returns_sorted_intervals_per_weekday(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, _query):
            return DummyResult(
                [
                    (1, time(13, 30), time(15, 0)),
                    (1, time(9, 0), time(12, 0)),
                    (5, time(10, 15), time(11, 45)),
                ]
            )

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    actual = await specialist_schedule.get_specialist_schedule(specialist_id)

    assert actual[1] == [{"start": "09:00", "end": "12:00"}, {"start": "13:30", "end": "15:00"}]
    assert actual[5] == [{"start": "10:15", "end": "11:45"}]
    assert actual[0] == []
    assert actual[6] == []


@pytest.mark.asyncio
async def test_get_specialist_schedule_returns_empty_lists_when_no_rows(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, _query):
            return DummyResult([])

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    actual = await specialist_schedule.get_specialist_schedule(specialist_id)

    assert actual == {weekday: [] for weekday in range(7)}


@pytest.mark.asyncio
async def test_validate_schedule_interval_rejects_invalid_time_order():
    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.validate_schedule_interval(uuid.uuid4(), 1, time(12, 0), time(12, 0))


@pytest.mark.asyncio
async def test_validate_schedule_interval_rejects_overlap(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, _query):
            return DummyResult([(time(10, 0), time(11, 0))])

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.validate_schedule_interval(specialist_id, 2, time(10, 30), time(11, 30))


@pytest.mark.asyncio
async def test_validate_schedule_interval_allows_non_overlapping(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, _query):
            return DummyResult([(time(10, 0), time(11, 0))])

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    await specialist_schedule.validate_schedule_interval(specialist_id, 2, time(11, 0), time(12, 0))


@pytest.mark.asyncio
async def test_add_working_interval_calls_cache_invalidate_and_returns_schedule(monkeypatch):
    specialist_id = uuid.uuid4()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def __init__(self):
            self.added = None

        def begin(self):
            return Tx()

        def add(self, value):
            self.added = value

    session = Session()
    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(session))

    calls = {"validate": 0, "invalidate": 0, "warn": 0}

    async def fake_validate(*args):
        calls["validate"] += 1

    async def fake_invalidate(_specialist_id):
        calls["invalidate"] += 1
        assert _specialist_id == specialist_id

    async def fake_warn(_specialist_id):
        calls["warn"] += 1
        assert _specialist_id == specialist_id

    expected = {weekday: [] for weekday in range(7)}

    async def fake_get_schedule(_specialist_id):
        assert _specialist_id == specialist_id
        return expected

    monkeypatch.setattr(specialist_schedule, "validate_schedule_interval", fake_validate)
    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)
    monkeypatch.setattr(specialist_schedule, "_warn_future_confirmed_outside_schedule", fake_warn)
    monkeypatch.setattr(specialist_schedule, "get_specialist_schedule", fake_get_schedule)

    actual = await specialist_schedule.add_working_interval(specialist_id, 1, time(9, 0), time(10, 0))

    assert session.added is not None
    assert calls == {"validate": 1, "invalidate": 1, "warn": 1}
    assert actual == expected


@pytest.mark.asyncio
async def test_delete_working_interval_deletes_and_returns_updated_schedule(monkeypatch):
    specialist_id = uuid.uuid4()
    interval = object()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def __init__(self):
            self.deleted = None

        def begin(self):
            return Tx()

        async def execute(self, _query):
            return DummyScalarResult(interval)

        async def delete(self, value):
            self.deleted = value

    session = Session()

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(session))

    calls = {"invalidate": 0, "warn": 0}

    async def fake_invalidate(_specialist_id):
        calls["invalidate"] += 1
        assert _specialist_id == specialist_id

    async def fake_warn(_specialist_id):
        calls["warn"] += 1
        assert _specialist_id == specialist_id

    expected = {weekday: [] for weekday in range(7)}

    async def fake_get_schedule(_specialist_id):
        assert _specialist_id == specialist_id
        return expected

    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)
    monkeypatch.setattr(specialist_schedule, "_warn_future_confirmed_outside_schedule", fake_warn)
    monkeypatch.setattr(specialist_schedule, "get_specialist_schedule", fake_get_schedule)

    actual = await specialist_schedule.delete_working_interval(uuid.uuid4(), specialist_id)

    assert session.deleted is interval
    assert calls == {"invalidate": 1, "warn": 1}
    assert actual == expected


@pytest.mark.asyncio
async def test_delete_working_interval_rejects_foreign_interval(monkeypatch):
    specialist_id = uuid.uuid4()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def execute(self, _query):
            return DummyScalarResult(None)

        async def delete(self, value):
            raise AssertionError(f"delete must not be called: {value}")

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.delete_working_interval(uuid.uuid4(), specialist_id)
