from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest

from services.availability_service import AvailabilityService, SpecialistAvailabilityContext


@dataclass
class FakeRepository:
    context: SpecialistAvailabilityContext

    async def get_specialist_timezone(self, specialist_id):
        return self.context.specialist_tz

    async def get_context_for_date(self, specialist_id, target_date_local_specialist):
        return self.context


@dataclass
class FakeBusyProvider:
    busy: list[tuple[datetime, datetime]]

    async def get_busy_for_local_day(self, **kwargs):
        return self.busy


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_applies_pipeline_and_groups_parts_of_day() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=15,
        max_sessions_per_day=4,
        slot_step_min=30,
        intervals=[(time(9, 0), time(11, 0)), (time(11, 0), time(13, 0))],
        cancel_window_hours=12,
    )
    busy = [(datetime(2026, 2, 12, 10, 0), datetime(2026, 2, 12, 11, 0))]
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider(busy),
        now_utc_provider=lambda: datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
    )

    assert slots == {
        "morning": [datetime(2026, 2, 12, 11, 30), datetime(2026, 2, 12, 12, 0)],
        "day": [],
        "evening": [],
    }


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_returns_all_candidates_without_top4_trimming() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=20,
        slot_step_min=30,
        intervals=[(time(9, 0), time(15, 0))],
        cancel_window_hours=12,
    )
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider([]),
        now_utc_provider=lambda: datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
    )

    all_slots = slots["morning"] + slots["day"] + slots["evening"]
    assert len(all_slots) == 11
    assert all_slots[0] == datetime(2026, 2, 12, 9, 0)
    assert all_slots[-1] == datetime(2026, 2, 12, 14, 0)


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_returns_empty_when_daily_limit_reached() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=1,
        slot_step_min=30,
        intervals=[(time(9, 0), time(12, 0))],
        cancel_window_hours=12,
    )
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider([(datetime(2026, 2, 12, 10, 0), datetime(2026, 2, 12, 11, 0))]),
        now_utc_provider=lambda: datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
    )

    assert slots == {"morning": [], "day": [], "evening": []}


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_applies_min_hours_window() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=4,
        slot_step_min=30,
        intervals=[(time(9, 0), time(12, 0))],
        cancel_window_hours=12,
    )
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider([]),
        now_utc_provider=lambda: datetime(2026, 2, 11, 22, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
    )

    assert slots["morning"] == [
        datetime(2026, 2, 12, 10, 0),
        datetime(2026, 2, 12, 10, 30),
        datetime(2026, 2, 12, 11, 0),
    ]


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_range_uses_selected_bounds() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=15,
        max_sessions_per_day=4,
        slot_step_min=30,
        intervals=[(time(9, 0), time(18, 0))],
        cancel_window_hours=12,
    )
    busy = [(datetime(2026, 2, 12, 13, 0), datetime(2026, 2, 12, 14, 0))]
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider(busy),
        now_utc_provider=lambda: datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date_range(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
        interval_start=time(12, 0),
        interval_end=time(16, 0),
    )

    assert slots == [datetime(2026, 2, 12, 14, 30), datetime(2026, 2, 12, 15, 0)]


@pytest.mark.asyncio
async def test_get_candidate_slots_for_date_range_applies_packing_and_limits_to_six() -> None:
    context = SpecialistAvailabilityContext(
        specialist_tz="UTC",
        session_duration_min=60,
        session_buffer_min=0,
        max_sessions_per_day=8,
        slot_step_min=30,
        intervals=[(time(9, 0), time(18, 0))],
        cancel_window_hours=12,
    )
    busy = [(datetime(2026, 2, 12, 13, 0), datetime(2026, 2, 12, 14, 0))]
    service = AvailabilityService(
        repository=FakeRepository(context),
        busy_provider=FakeBusyProvider(busy),
        now_utc_provider=lambda: datetime(2026, 2, 11, 10, 0, tzinfo=timezone.utc),
    )

    slots = await service.get_candidate_slots_for_date_range(
        specialist_id=uuid4(),
        target_date_local_client=date(2026, 2, 12),
        client_tz="UTC",
        interval_start=time(9, 0),
        interval_end=time(18, 0),
    )

    assert slots == [
        datetime(2026, 2, 12, 12, 0),
        datetime(2026, 2, 12, 14, 0),
        datetime(2026, 2, 12, 9, 0),
        datetime(2026, 2, 12, 9, 30),
        datetime(2026, 2, 12, 10, 0),
        datetime(2026, 2, 12, 10, 30),
    ]


def test_split_by_part_of_day_uses_new_boundaries() -> None:
    starts = [
        datetime(2026, 2, 12, 12, 30),
        datetime(2026, 2, 12, 13, 0),
        datetime(2026, 2, 12, 16, 30),
        datetime(2026, 2, 12, 17, 0),
    ]

    slots = AvailabilityService._split_by_part_of_day(starts)

    assert slots == {
        "morning": [datetime(2026, 2, 12, 12, 30)],
        "day": [datetime(2026, 2, 12, 13, 0), datetime(2026, 2, 12, 16, 30)],
        "evening": [datetime(2026, 2, 12, 17, 0)],
    }

@pytest.mark.asyncio
async def test_get_context_for_date_reads_working_intervals_merges_and_filters(monkeypatch):
    import uuid

    import services.availability_service as availability_service

    specialist_id = uuid.uuid4()

    class _Session:
        async def get(self, model, _sid):
            if model is availability_service.SpecialistProfile:
                return type(
                    "Profile",
                    (),
                    {
                        "specialist_timezone": "UTC",
                        "session_duration_min": 60,
                        "session_buffer_min": 10,
                        "max_sessions_per_day": 4,
                        "slot_step_min": 30,
                        "cancel_window_hours": 12,
                    },
                )()
            return None

        async def execute(self, _stmt):
            class _Result:
                def all(self):
                    # 1) short interval should be filtered out (20 min < 60)
                    # 2) stitched intervals should merge into one 11:00-15:00
                    return [
                        (540, 560),
                        (660, 780),
                        (780, 900),
                    ]

            return _Result()

    class _SessionCtx:
        async def __aenter__(self):
            return _Session()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _ensure(_specialist_id):
        assert _specialist_id == specialist_id
        return False

    monkeypatch.setattr(availability_service, "async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(availability_service, "ensure_default_working_intervals", _ensure)

    repo = availability_service.AvailabilityRepository()
    context = await repo.get_context_for_date(specialist_id, date(2026, 2, 12))

    assert context.intervals == [(time(11, 0), time(15, 0))]
