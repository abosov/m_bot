import uuid

import pytest

from services.working_intervals_repository import WorkingIntervalsRepository


class _ExecuteAllResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DummySession:
    def __init__(self, *, rows=None):
        self._rows = rows or []
        self.executed_statements = []
        self.committed = 0

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _ExecuteAllResult(self._rows)

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
async def test_get_working_intervals_returns_defaults_with_existing_rows(monkeypatch):
    specialist_id = uuid.uuid4()
    session = _DummySession(rows=[(1, 540, 720), (3, None, None)])

    import services.working_intervals_repository as repo_module

    monkeypatch.setattr(repo_module, "async_session_factory", lambda: _DummySessionCtx(session))
    repo = WorkingIntervalsRepository()

    result = await repo.get_working_intervals(specialist_id)

    assert result == {
        1: (540, 720),
        2: (None, None),
        3: (None, None),
    }


@pytest.mark.asyncio
async def test_upsert_working_intervals_executes_once_and_commits(monkeypatch):
    specialist_id = uuid.uuid4()
    session = _DummySession()

    import services.working_intervals_repository as repo_module

    monkeypatch.setattr(repo_module, "async_session_factory", lambda: _DummySessionCtx(session))
    repo = WorkingIntervalsRepository()

    await repo.upsert_working_intervals(
        specialist_id,
        {
            1: (540, 720),
            2: (780, 1020),
            3: (1020, 1260),
        },
    )

    assert len(session.executed_statements) == 1
    assert session.committed == 1
