import uuid
from datetime import time

import pytest

from database import SpecialistAuthTelegram, SpecialistProfile, WeeklyAvailability
from services import specialist_defaults


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


class DummySession:
    def __init__(self, *, profile=None, auth=None, weekly_rows=None):
        self._profile = profile
        self._auth = auth
        self._weekly_rows = weekly_rows or []
        self.added = []
        self.flushed = False

    async def get(self, model, _sid):
        if model is SpecialistProfile:
            return self._profile
        if model is SpecialistAuthTelegram:
            return self._auth
        return None

    async def execute(self, _query):
        return _ExecuteResult(self._weekly_rows)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_apply_defaults_creates_profile_and_weekly_if_missing():
    specialist_id = uuid.uuid4()
    auth = SpecialistAuthTelegram(
        specialist_id=specialist_id,
        tg_user_id=777,
        tg_username="owner",
        tg_first_name=None,
        tg_last_name=None,
    )
    session = DummySession(profile=None, auth=auth, weekly_rows=[])

    await specialist_defaults.apply_specialist_defaults_if_missing(
        session,
        specialist_id,
        preferred_timezone="Europe/Berlin",
    )

    created_profile = next(obj for obj in session.added if isinstance(obj, SpecialistProfile))
    weekly = [obj for obj in session.added if isinstance(obj, WeeklyAvailability)]

    assert created_profile.specialist_timezone == "Europe/Berlin"
    assert created_profile.session_duration_min == 60
    assert created_profile.session_buffer_min == 10
    assert created_profile.cancel_window_hours == 12
    assert created_profile.max_sessions_per_day == 4
    assert created_profile.slot_step_min == 15

    assert len(weekly) == 7
    mon = next(row for row in weekly if row.weekday == 0)
    sat = next(row for row in weekly if row.weekday == 5)
    assert mon.is_working is True
    assert mon.interval_1_start == time(9, 0)
    assert mon.interval_3_end == time(21, 0)
    assert sat.is_working is False
    assert sat.interval_1_start is None
    assert session.flushed is True


@pytest.mark.asyncio
async def test_apply_defaults_does_not_override_existing_weekly():
    specialist_id = uuid.uuid4()
    profile = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="Spec",
        owner_tg_user_id=1,
        owner_tg_username=None,
        specialist_timezone="",
        session_duration_min=60,
        session_buffer_min=10,
        cancel_window_hours=12,
        max_sessions_per_day=4,
        slot_step_min=15,
    )
    existing_weekly = [
        WeeklyAvailability(specialist_id=specialist_id, weekday=idx, is_working=(idx < 5))
        for idx in range(7)
    ]
    session = DummySession(profile=profile, auth=None, weekly_rows=existing_weekly)

    await specialist_defaults.apply_specialist_defaults_if_missing(session, specialist_id)

    assert all(not isinstance(obj, WeeklyAvailability) for obj in session.added)
    assert profile.specialist_timezone == "UTC"


@pytest.mark.asyncio
async def test_apply_defaults_uses_utc_when_timezone_not_provided():
    specialist_id = uuid.uuid4()
    profile = SpecialistProfile(
        specialist_id=specialist_id,
        public_name="Spec",
        owner_tg_user_id=1,
        owner_tg_username=None,
        specialist_timezone="",
        session_duration_min=60,
        session_buffer_min=10,
        cancel_window_hours=12,
        max_sessions_per_day=4,
        slot_step_min=15,
    )
    session = DummySession(profile=profile, weekly_rows=[WeeklyAvailability(specialist_id=specialist_id, weekday=i, is_working=False) for i in range(7)])

    await specialist_defaults.apply_specialist_defaults_if_missing(
        session,
        specialist_id,
        preferred_timezone=None,
    )

    assert profile.specialist_timezone == "UTC"
