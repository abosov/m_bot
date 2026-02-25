import uuid

import pytest

from services.working_intervals import WorkingIntervalsValidationError, apply_interval_edit


class _DummyRepo:
    def __init__(self, *, intervals):
        self._intervals = intervals
        self.saved = None

    async def get_working_intervals(self, _specialist_id):
        return dict(self._intervals)

    async def upsert_working_intervals(self, _specialist_id, intervals_dict):
        self.saved = dict(intervals_dict)


@pytest.mark.asyncio
async def test_apply_interval_edit_set_normalizes_and_saves(monkeypatch):
    specialist_id = uuid.uuid4()
    repo = _DummyRepo(
        intervals={
            1: (540, 720),
            2: (780, 1020),
            3: (1020, 1260),
        }
    )

    import services.working_intervals as service_module

    async def _noop(_specialist_id):
        return False

    monkeypatch.setattr(service_module, "ensure_default_working_intervals", _noop)
    monkeypatch.setattr(service_module, "WorkingIntervalsRepository", lambda: repo)

    result = await apply_interval_edit(
        specialist_id=specialist_id,
        idx=1,
        new_start_min=540,
        new_end_min=900,
        action="set",
    )

    assert result == {
        1: (540, 900),
        2: (900, 1020),
        3: (1020, 1260),
    }
    assert repo.saved == result


@pytest.mark.asyncio
async def test_apply_interval_edit_disable_persists_null_pair(monkeypatch):
    specialist_id = uuid.uuid4()
    repo = _DummyRepo(
        intervals={
            1: (540, 720),
            2: (780, 1020),
            3: (1020, 1260),
        }
    )

    import services.working_intervals as service_module

    async def _noop(_specialist_id):
        return False

    monkeypatch.setattr(service_module, "ensure_default_working_intervals", _noop)
    monkeypatch.setattr(service_module, "WorkingIntervalsRepository", lambda: repo)

    result = await apply_interval_edit(
        specialist_id=specialist_id,
        idx=2,
        new_start_min=None,
        new_end_min=None,
        action="disable",
    )

    assert result[2] == (None, None)
    assert repo.saved[2] == (None, None)


@pytest.mark.asyncio
async def test_apply_interval_edit_validates_set_range():
    specialist_id = uuid.uuid4()

    with pytest.raises(WorkingIntervalsValidationError, match="0 <= start < end <= 1440"):
        await apply_interval_edit(
            specialist_id=specialist_id,
            idx=1,
            new_start_min=800,
            new_end_min=700,
            action="set",
        )
