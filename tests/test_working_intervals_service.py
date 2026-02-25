import uuid

import pytest

from database import SpecialistWorkingInterval
from services import working_intervals


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _Scalars(self._rows)


class _DummySession:
    def __init__(self, existing_idx):
        self._existing_idx = existing_idx
        self.added = []
        self.committed = 0

    async def execute(self, _query):
        return _ExecuteResult(self._existing_idx)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1


class _DummySessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_ensure_default_working_intervals_creates_missing_rows(monkeypatch):
    specialist_id = uuid.uuid4()
    session = _DummySession(existing_idx=[2])
    monkeypatch.setattr(working_intervals, "async_session_factory", lambda: _DummySessionCtx(session))

    changed = await working_intervals.ensure_default_working_intervals(specialist_id)

    assert changed is True
    assert session.committed == 1
    assert len(session.added) == 2

    rows = [row for row in session.added if isinstance(row, SpecialistWorkingInterval)]
    assert {row.idx for row in rows} == {1, 3}
    interval_by_idx = {row.idx: (row.start_min, row.end_min) for row in rows}
    assert interval_by_idx[1] == (540, 720)
    assert interval_by_idx[3] == (1020, 1260)


@pytest.mark.asyncio
async def test_ensure_default_working_intervals_is_noop_when_rows_exist(monkeypatch):
    specialist_id = uuid.uuid4()
    session = _DummySession(existing_idx=[1, 2, 3])
    monkeypatch.setattr(working_intervals, "async_session_factory", lambda: _DummySessionCtx(session))

    changed = await working_intervals.ensure_default_working_intervals(specialist_id)

    assert changed is False
    assert session.committed == 0
    assert session.added == []
