from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Protocol
from uuid import UUID

from services.availability_service import AvailabilityService
from services.slot_ranking import rank_slots_for_interval

INTERVALS = ("morning", "day", "evening")
_INTERVAL_SET = set(INTERVALS)

FSM_SELECTED_DATE_KEY = "client_flow_selected_date"
FSM_SELECTED_INTERVALS_KEY = "client_flow_selected_intervals"

CALLBACK_PICK_WEEKDAY = "client_pick_weekday"
CALLBACK_TOGGLE_INTERVAL = "client_toggle_interval"
CALLBACK_SHOW_SLOTS = "client_show_slots"
CALLBACK_PICK_SLOT = "client_pick_slot"


class FSMStateProtocol(Protocol):
    async def get_data(self) -> dict: ...

    async def update_data(self, **kwargs) -> dict: ...


@dataclass(slots=True)
class ClientSlotsView:
    target_date: date
    selected_intervals: tuple[str, ...]
    slots_by_interval: dict[str, list[datetime]]
    empty_intervals: tuple[str, ...]
    is_day_empty: bool
    is_selection_empty: bool


class ClientFlowService:
    def __init__(self, *, availability_service: AvailabilityService | None = None) -> None:
        self._availability_service = availability_service or AvailabilityService()

    async def choose_weekday(self, state: FSMStateProtocol, callback_data: str) -> date:
        target_date = parse_pick_weekday_callback(callback_data)
        await state.update_data(
            **{
                FSM_SELECTED_DATE_KEY: target_date.isoformat(),
                FSM_SELECTED_INTERVALS_KEY: [],
            }
        )
        return target_date

    async def toggle_interval(self, state: FSMStateProtocol, callback_data: str) -> tuple[date, tuple[str, ...]]:
        target_date, interval = parse_toggle_interval_callback(callback_data)
        data = await state.get_data()

        selected_date_raw = data.get(FSM_SELECTED_DATE_KEY)
        selected_intervals = _normalize_intervals(data.get(FSM_SELECTED_INTERVALS_KEY, []))

        if selected_date_raw != target_date.isoformat():
            selected_intervals = []

        if interval in selected_intervals:
            selected_intervals = [value for value in selected_intervals if value != interval]
        else:
            selected_intervals.append(interval)

        selected_intervals = sorted(selected_intervals, key=INTERVALS.index)
        await state.update_data(
            **{
                FSM_SELECTED_DATE_KEY: target_date.isoformat(),
                FSM_SELECTED_INTERVALS_KEY: selected_intervals,
            }
        )

        return target_date, tuple(selected_intervals)

    async def build_slots_view(
        self,
        *,
        state: FSMStateProtocol,
        specialist_id: UUID,
        client_tz: str,
        callback_data: str,
    ) -> ClientSlotsView:
        target_date = parse_show_slots_callback(callback_data)
        state_data = await state.get_data()

        selected_intervals = _normalize_intervals(state_data.get(FSM_SELECTED_INTERVALS_KEY, []))
        selected_date_raw = state_data.get(FSM_SELECTED_DATE_KEY)
        if selected_date_raw != target_date.isoformat():
            selected_intervals = []

        if not selected_intervals:
            return ClientSlotsView(
                target_date=target_date,
                selected_intervals=tuple(),
                slots_by_interval={interval: [] for interval in INTERVALS},
                empty_intervals=tuple(),
                is_day_empty=True,
                is_selection_empty=True,
            )

        available_by_interval = await self._availability_service.get_candidate_slots_for_date(
            specialist_id=specialist_id,
            target_date_local_client=target_date,
            client_tz=client_tz,
        )

        ranked: dict[str, list[datetime]] = {interval: [] for interval in INTERVALS}
        for interval in selected_intervals:
            ranked[interval] = _rank_interval_slots(
                target_date=target_date,
                interval=interval,
                candidates=available_by_interval.get(interval, []),
            )

        empty_intervals = tuple(interval for interval in selected_intervals if not ranked.get(interval))
        has_any = any(ranked.get(interval) for interval in selected_intervals)
        return ClientSlotsView(
            target_date=target_date,
            selected_intervals=tuple(selected_intervals),
            slots_by_interval=ranked,
            empty_intervals=empty_intervals,
            is_day_empty=not has_any,
            is_selection_empty=False,
        )


def parse_pick_weekday_callback(callback_data: str) -> date:
    prefix = f"{CALLBACK_PICK_WEEKDAY}:"
    if not callback_data.startswith(prefix):
        raise ValueError("Unsupported callback for weekday pick")
    return _parse_date(callback_data[len(prefix) :])


def parse_toggle_interval_callback(callback_data: str) -> tuple[date, str]:
    prefix = f"{CALLBACK_TOGGLE_INTERVAL}:"
    if not callback_data.startswith(prefix):
        raise ValueError("Unsupported callback for interval toggle")

    payload = callback_data[len(prefix) :]
    date_raw, interval = payload.split(":", 1)
    if interval not in _INTERVAL_SET:
        raise ValueError("Unsupported interval in callback")
    return _parse_date(date_raw), interval


def parse_show_slots_callback(callback_data: str) -> date:
    prefix = f"{CALLBACK_SHOW_SLOTS}:"
    if not callback_data.startswith(prefix):
        raise ValueError("Unsupported callback for show slots")
    return _parse_date(callback_data[len(prefix) :])


def parse_pick_slot_callback(callback_data: str) -> datetime:
    prefix = f"{CALLBACK_PICK_SLOT}:"
    if not callback_data.startswith(prefix):
        raise ValueError("Unsupported callback for slot pick")

    raw = callback_data[len(prefix) :]
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Invalid callback date") from exc


def _normalize_intervals(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    filtered = [value for value in raw if isinstance(value, str) and value in _INTERVAL_SET]
    return sorted(set(filtered), key=INTERVALS.index)


def _rank_interval_slots(*, target_date: date, interval: str, candidates: list[datetime]) -> list[datetime]:
    start_time, end_time = _interval_bounds(interval)
    interval_start = datetime.combine(target_date, start_time)
    interval_end = datetime.combine(target_date, end_time)

    return rank_slots_for_interval(
        interval_start=interval_start,
        interval_end=interval_end,
        candidate_starts=sorted(candidates),
        existing_confirmed_sessions=[],
        session_duration=60,
        buffer_minutes=0,
        max_results=4,
    )


def _interval_bounds(interval: str) -> tuple[time, time]:
    if interval == "morning":
        return time(0, 0), time(12, 0)
    if interval == "day":
        return time(12, 0), time(18, 0)
    return time(18, 0), time(23, 59, 59)
