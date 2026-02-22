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


@pytest.mark.asyncio
async def test_update_specialist_timezone_updates_profile_invalidates_cache_and_returns_values(monkeypatch):
    specialist_id = uuid.uuid4()
    profile = type("Profile", (), {"specialist_timezone": "UTC"})()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    calls = {"invalidate": 0}

    async def fake_invalidate(sid):
        calls["invalidate"] += 1
        assert sid == specialist_id

    async def fake_warn(_sid):
        raise AssertionError("update_specialist_timezone must not touch existing sessions")

    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)
    monkeypatch.setattr(specialist_schedule, "_warn_future_confirmed_outside_schedule", fake_warn)

    actual = await specialist_schedule.update_specialist_timezone(specialist_id, "Europe/Berlin")

    assert profile.specialist_timezone == "Europe/Berlin"
    assert calls == {"invalidate": 1}
    assert actual == {"specialist_timezone": "Europe/Berlin"}


@pytest.mark.asyncio
async def test_update_specialist_timezone_raises_for_invalid_timezone():
    with pytest.raises(specialist_schedule.ValidationError, match="timezone does not exist"):
        await specialist_schedule.update_specialist_timezone(uuid.uuid4(), "Mars/Olympus")


@pytest.mark.asyncio
async def test_update_specialist_timezone_raises_when_profile_not_found(monkeypatch):
    specialist_id = uuid.uuid4()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return None

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError, match="specialist profile not found"):
        await specialist_schedule.update_specialist_timezone(specialist_id, "UTC")


@pytest.mark.asyncio
async def test_update_session_settings_validates_inputs() -> None:
    specialist_id = uuid.uuid4()

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.update_session_settings(specialist_id, duration=10, buffer=0)

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.update_session_settings(specialist_id, duration=30, buffer=121)


@pytest.mark.asyncio
async def test_update_session_settings_updates_profile_invalidates_cache_and_returns_values(monkeypatch):
    specialist_id = uuid.uuid4()
    profile = type("Profile", (), {"session_duration_min": 60, "session_buffer_min": 0})()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    calls = {"invalidate": 0}

    async def fake_invalidate(sid):
        calls["invalidate"] += 1
        assert sid == specialist_id

    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)

    actual = await specialist_schedule.update_session_settings(specialist_id, duration=45, buffer=15)

    assert profile.session_duration_min == 45
    assert profile.session_buffer_min == 15
    assert calls == {"invalidate": 1}
    assert actual == {"session_duration_min": 45, "session_buffer_min": 15}


@pytest.mark.asyncio
async def test_update_session_settings_raises_when_profile_not_found(monkeypatch):
    specialist_id = uuid.uuid4()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return None

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.update_session_settings(specialist_id, duration=45, buffer=15)


@pytest.mark.asyncio
async def test_update_limits_validates_inputs(monkeypatch) -> None:
    specialist_id = uuid.uuid4()
    profile = type("Profile", (), {"session_duration_min": 60, "max_sessions_per_day": 4, "slot_step_min": 15})()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.update_limits(specialist_id, max_per_day=0, slot_step=15)


@pytest.mark.asyncio
async def test_update_limits_updates_profile_invalidates_cache_and_returns_values(monkeypatch):
    specialist_id = uuid.uuid4()
    profile = type("Profile", (), {"session_duration_min": 60, "max_sessions_per_day": 4, "slot_step_min": 15})()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    calls = {"invalidate": 0}

    async def fake_invalidate(sid):
        calls["invalidate"] += 1
        assert sid == specialist_id

    async def fake_warn(_sid):
        raise AssertionError("update_limits must not touch existing sessions")

    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)
    monkeypatch.setattr(specialist_schedule, "_warn_future_confirmed_outside_schedule", fake_warn)

    actual = await specialist_schedule.update_limits(specialist_id, max_per_day=20, slot_step=10)

    assert profile.max_sessions_per_day == 20
    assert profile.slot_step_min == 10
    assert calls == {"invalidate": 1}
    assert actual == {"max_sessions_per_day": 20, "slot_step_min": 10}


@pytest.mark.asyncio
async def test_update_limits_raises_when_slot_step_gt_duration(monkeypatch):
    specialist_id = uuid.uuid4()
    profile = type("Profile", (), {"session_duration_min": 30, "max_sessions_per_day": 4, "slot_step_min": 15})()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError):
        await specialist_schedule.update_limits(specialist_id, max_per_day=4, slot_step=35)


@pytest.mark.asyncio
async def test_reset_specialist_settings_to_default_resets_profile_schedule_and_invalidates_cache(monkeypatch):
    specialist_id = uuid.uuid4()
    profile = type(
        "Profile",
        (),
        {
            "session_duration_min": 90,
            "session_buffer_min": 20,
            "slot_step_min": 30,
            "max_sessions_per_day": 10,
        },
    )()

    class Scalars:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class ExecResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return Scalars(self._rows)

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def __init__(self):
            self.deleted = []
            self.added = []

        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return profile

        async def execute(self, _query):
            return ExecResult([object(), object()])

        async def delete(self, value):
            self.deleted.append(value)

        def add(self, value):
            self.added.append(value)

    session = Session()
    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(session))

    calls = {"invalidate": 0}

    async def fake_invalidate(sid):
        calls["invalidate"] += 1
        assert sid == specialist_id

    expected_schedule = {weekday: [] for weekday in range(7)}

    async def fake_get_schedule(sid):
        assert sid == specialist_id
        return expected_schedule

    monkeypatch.setattr(specialist_schedule, "invalidate_availability_cache", fake_invalidate)
    monkeypatch.setattr(specialist_schedule, "get_specialist_schedule", fake_get_schedule)

    actual = await specialist_schedule.reset_specialist_settings_to_default(specialist_id)

    assert profile.session_duration_min == specialist_schedule.DEFAULT_DURATION_MIN
    assert profile.session_buffer_min == specialist_schedule.DEFAULT_BUFFER_MIN
    assert profile.slot_step_min == specialist_schedule.DEFAULT_SLOT_STEP_MIN
    assert profile.max_sessions_per_day == specialist_schedule.DEFAULT_MAX_SESSIONS_PER_DAY
    assert len(session.deleted) == 2
    assert len(session.added) == len(specialist_schedule.DEFAULT_WORKING_DAYS) * len(specialist_schedule.DEFAULT_WORKING_INTERVALS)
    assert calls == {"invalidate": 1}
    assert actual == {
        "session_duration_min": specialist_schedule.DEFAULT_DURATION_MIN,
        "session_buffer_min": specialist_schedule.DEFAULT_BUFFER_MIN,
        "slot_step_min": specialist_schedule.DEFAULT_SLOT_STEP_MIN,
        "max_sessions_per_day": specialist_schedule.DEFAULT_MAX_SESSIONS_PER_DAY,
        "schedule": expected_schedule,
    }


@pytest.mark.asyncio
async def test_reset_specialist_settings_to_default_raises_when_profile_not_found(monkeypatch):
    specialist_id = uuid.uuid4()

    class Tx:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class Session:
        def begin(self):
            return Tx()

        async def get(self, model, sid):
            assert sid == specialist_id
            return None

    monkeypatch.setattr(specialist_schedule, "async_session_factory", lambda: DummySessionCtx(Session()))

    with pytest.raises(specialist_schedule.ValidationError, match="specialist profile not found"):
        await specialist_schedule.reset_specialist_settings_to_default(specialist_id)
