from __future__ import annotations

import logging
import uuid

import pytest

from database import WeeklyAvailability
from services import weekly_availability


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
async def test_get_working_days_creates_missing_rows_and_commits(monkeypatch):
    specialist_id = uuid.uuid4()
    rows = [WeeklyAvailability(specialist_id=specialist_id, weekday=0, is_working=True)]

    class Session:
        def __init__(self):
            self.added: list[WeeklyAvailability] = []
            self.commits = 0
            self.flushes = 0

        async def execute(self, _query):
            return DummyResult(rows)

        def add(self, row):
            self.added.append(row)

        async def flush(self):
            self.flushes += 1

        async def commit(self):
            self.commits += 1

    session = Session()
    monkeypatch.setattr(weekly_availability, "async_session_factory", lambda: DummySessionCtx(session))

    actual = await weekly_availability.get_working_days(specialist_id)

    assert actual == {0, 1, 2, 3, 4}
    assert len(session.added) == 6
    assert session.flushes == 1
    assert session.commits == 1


@pytest.mark.asyncio
async def test_toggle_working_day_updates_state_logs_and_commits(monkeypatch):
    specialist_id = uuid.uuid4()
    rows = [
        WeeklyAvailability(specialist_id=specialist_id, weekday=weekday, is_working=(weekday in {0, 1, 2, 3, 4}))
        for weekday in range(7)
    ]

    class Session:
        def __init__(self):
            self.commits = 0

        async def execute(self, _query):
            return DummyResult(rows)

        def add(self, _row):
            raise AssertionError("add should not be called when all rows exist")

        async def flush(self):
            raise AssertionError("flush should not be called when all rows exist")

        async def commit(self):
            self.commits += 1

    session = Session()
    monkeypatch.setattr(weekly_availability, "async_session_factory", lambda: DummySessionCtx(session))

    logged = {}

    def fake_log_event(_logger, _level, *, event: str, **fields):
        logged["event"] = event
        logged["level"] = _level
        logged.update(fields)

    monkeypatch.setattr(weekly_availability, "log_event", fake_log_event)

    actual = await weekly_availability.toggle_working_day(specialist_id, 5)

    assert actual == {0, 1, 2, 3, 4, 5}
    assert session.commits == 1
    assert logged == {
        "event": "weekly_availability_day_toggled",
        "level": logging.INFO,
        "specialist_id": str(specialist_id),
        "weekday": 5,
        "is_working": True,
    }


@pytest.mark.asyncio
async def test_set_working_day_updates_day_and_commits(monkeypatch):
    specialist_id = uuid.uuid4()
    rows = [
        WeeklyAvailability(specialist_id=specialist_id, weekday=weekday, is_working=(weekday in {0, 1, 2, 3, 4}))
        for weekday in range(7)
    ]

    class Session:
        def __init__(self):
            self.commits = 0

        async def execute(self, _query):
            return DummyResult(rows)

        def add(self, _row):
            raise AssertionError("add should not be called when all rows exist")

        async def flush(self):
            raise AssertionError("flush should not be called when all rows exist")

        async def commit(self):
            self.commits += 1

    session = Session()
    monkeypatch.setattr(weekly_availability, "async_session_factory", lambda: DummySessionCtx(session))

    await weekly_availability.set_working_day(specialist_id, 2, False)

    assert rows[2].is_working is False
    assert session.commits == 1


@pytest.mark.asyncio
async def test_toggle_working_day_validates_weekday():
    with pytest.raises(ValueError):
        await weekly_availability.toggle_working_day(uuid.uuid4(), 7)


@pytest.mark.asyncio
async def test_set_working_day_validates_weekday():
    with pytest.raises(ValueError):
        await weekly_availability.set_working_day(uuid.uuid4(), -1, True)


@pytest.mark.asyncio
async def test_toggle_working_day_toggles_false_to_true_and_back(monkeypatch):
    specialist_id = uuid.uuid4()
    rows = [
        WeeklyAvailability(specialist_id=specialist_id, weekday=weekday, is_working=False)
        for weekday in range(7)
    ]

    class Session:
        def __init__(self):
            self.commits = 0

        async def execute(self, _query):
            return DummyResult(rows)

        def add(self, _row):
            raise AssertionError("add should not be called when all rows exist")

        async def flush(self):
            raise AssertionError("flush should not be called when all rows exist")

        async def commit(self):
            self.commits += 1

    session = Session()
    monkeypatch.setattr(weekly_availability, "async_session_factory", lambda: DummySessionCtx(session))

    first = await weekly_availability.toggle_working_day(specialist_id, 1)
    second = await weekly_availability.toggle_working_day(specialist_id, 1)

    assert 1 in first
    assert 1 not in second
    assert rows[1].is_working is False
    assert session.commits == 2
