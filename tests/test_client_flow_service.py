from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from services.client_flow_service import (
    ClientFlowService,
    parse_pick_slot_callback,
    parse_pick_weekday_callback,
    parse_show_slots_callback,
    parse_toggle_interval_callback,
)


@dataclass
class FakeState:
    data: dict = field(default_factory=dict)

    async def get_data(self) -> dict:
        return dict(self.data)

    async def update_data(self, **kwargs) -> dict:
        self.data.update(kwargs)
        return dict(self.data)


@dataclass
class FakeAvailabilityService:
    result: dict[str, list[datetime]]

    async def get_candidate_slots_for_date(self, **kwargs):
        return self.result


@pytest.mark.asyncio
async def test_weekday_pick_and_interval_toggle_store_fsm_state() -> None:
    service = ClientFlowService(availability_service=FakeAvailabilityService(result={}))
    state = FakeState()

    chosen_date = await service.choose_weekday(state, "client_pick_weekday:2026-02-12")
    _, selected = await service.toggle_interval(state, "client_toggle_interval:2026-02-12:day")

    assert chosen_date == date(2026, 2, 12)
    assert selected == ("day",)
    assert state.data["client_flow_selected_date"] == "2026-02-12"
    assert state.data["client_flow_selected_intervals"] == ["day"]


@pytest.mark.asyncio
async def test_build_slots_view_returns_all_slots_without_ranking() -> None:
    availability = {
        "morning": [
            datetime(2026, 2, 12, 8, 0),
            datetime(2026, 2, 12, 8, 30),
            datetime(2026, 2, 12, 9, 0),
            datetime(2026, 2, 12, 9, 30),
            datetime(2026, 2, 12, 10, 0),
        ],
        "day": [
            datetime(2026, 2, 12, 12, 0),
            datetime(2026, 2, 12, 13, 0),
            datetime(2026, 2, 12, 14, 0),
            datetime(2026, 2, 12, 15, 0),
        ],
        "evening": [datetime(2026, 2, 12, 18, 0)],
    }
    service = ClientFlowService(availability_service=FakeAvailabilityService(result=availability))
    state = FakeState(
        data={
            "client_flow_selected_date": "2026-02-12",
            "client_flow_selected_intervals": ["morning", "day"],
        }
    )

    view = await service.build_slots_view(
        state=state,
        specialist_id=uuid4(),
        client_tz="UTC",
        callback_data="client_show_slots:2026-02-12",
    )

    assert len(view.slots_by_interval["morning"]) == 5
    assert len(view.slots_by_interval["day"]) == 4
    assert view.slots_by_interval["morning"][0] == datetime(2026, 2, 12, 8, 0)
    assert view.slots_by_interval["morning"][-1] == datetime(2026, 2, 12, 10, 0)
    assert view.empty_intervals == ()
    assert view.is_day_empty is False
    assert view.is_selection_empty is False


@pytest.mark.asyncio
async def test_build_slots_view_edge_cases() -> None:
    availability = {
        "morning": [],
        "day": [],
        "evening": [],
    }
    service = ClientFlowService(availability_service=FakeAvailabilityService(result=availability))

    state_empty_selection = FakeState(data={"client_flow_selected_date": "2026-02-12", "client_flow_selected_intervals": []})
    empty_selection = await service.build_slots_view(
        state=state_empty_selection,
        specialist_id=uuid4(),
        client_tz="UTC",
        callback_data="client_show_slots:2026-02-12",
    )
    assert empty_selection.is_selection_empty is True
    assert empty_selection.is_day_empty is True

    state_empty_interval = FakeState(
        data={"client_flow_selected_date": "2026-02-12", "client_flow_selected_intervals": ["morning"]}
    )
    empty_interval = await service.build_slots_view(
        state=state_empty_interval,
        specialist_id=uuid4(),
        client_tz="UTC",
        callback_data="client_show_slots:2026-02-12",
    )
    assert empty_interval.empty_intervals == ("morning",)
    assert empty_interval.is_day_empty is True


def test_callback_parsers() -> None:
    assert parse_pick_weekday_callback("client_pick_weekday:2026-02-12") == date(2026, 2, 12)
    assert parse_toggle_interval_callback("client_toggle_interval:2026-02-12:evening") == (
        date(2026, 2, 12),
        "evening",
    )
    assert parse_show_slots_callback("client_show_slots:2026-02-12") == date(2026, 2, 12)
    assert parse_pick_slot_callback("client_pick_slot:2026-02-12T10:00:00+03:00") == datetime(2026, 2, 12, 7, 0, tzinfo=timezone.utc)
