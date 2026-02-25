from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from database import SpecialistCalendarSettings, SpecialistProfile, SpecialistWorkingInterval, async_session_factory
from services.schedule_utils import merge_intervals
from services.slot_ranking import rank_slots_for_interval
from services.slot_step import iter_slot_starts
from services.working_intervals import ensure_default_working_intervals


@dataclass(slots=True)
class SpecialistAvailabilityContext:
    specialist_tz: str
    session_duration_min: int
    session_buffer_min: int
    max_sessions_per_day: int
    slot_step_min: int
    intervals: list[tuple[time, time]]
    cancel_window_hours: int


class AvailabilityRepository:
    async def get_specialist_timezone(self, specialist_id: UUID) -> str:
        async with async_session_factory() as session:
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValueError("Specialist profile not found")
            return profile.specialist_timezone

    async def get_context_for_date(self, specialist_id: UUID, target_date_local_specialist: date) -> SpecialistAvailabilityContext:
        await ensure_default_working_intervals(specialist_id)

        async with async_session_factory() as session:
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                raise ValueError("Specialist profile not found")

            interval_rows = (
                await session.execute(
                    select(
                        SpecialistWorkingInterval.start_min,
                        SpecialistWorkingInterval.end_min,
                    )
                    .where(SpecialistWorkingInterval.specialist_id == specialist_id)
                    .order_by(SpecialistWorkingInterval.idx.asc())
                )
            ).all()

        intervals: list[tuple[time, time]] = []
        required_min = profile.session_duration_min
        for start_min, end_min in interval_rows:
            if start_min is None or end_min is None:
                continue
            if start_min >= end_min:
                continue
            if (end_min - start_min) < required_min:
                continue
            intervals.append((_minutes_to_time(start_min), _minutes_to_time(end_min)))

        intervals = merge_intervals(intervals)

        return SpecialistAvailabilityContext(
            specialist_tz=profile.specialist_timezone,
            session_duration_min=profile.session_duration_min,
            session_buffer_min=profile.session_buffer_min,
            max_sessions_per_day=profile.max_sessions_per_day,
            slot_step_min=profile.slot_step_min,
            intervals=intervals,
            cancel_window_hours=(profile.cancel_window_hours or 12),
        )


def _minutes_to_time(value: int) -> time:
    hours, minutes = divmod(value, 60)
    return time(hours % 24, minutes)


class GoogleBusyProvider:
    async def get_busy_for_local_day(
        self,
        *,
        specialist_id: UUID,
        specialist_tz: str,
        target_date_local_specialist: date,
    ) -> list[tuple[datetime, datetime]]:
        from services.google_calendar import get_busy_intervals_for_day

        async with async_session_factory() as session:
            settings = await session.get(SpecialistCalendarSettings, specialist_id)
            if settings is None:
                return []

        return await get_busy_intervals_for_day(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            specialist_tz=specialist_tz,
            target_date_local_specialist=target_date_local_specialist,
        )


class AvailabilityService:
    def __init__(
        self,
        *,
        repository: AvailabilityRepository | None = None,
        busy_provider: GoogleBusyProvider | None = None,
        now_utc_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository or AvailabilityRepository()
        self._busy_provider = busy_provider or GoogleBusyProvider()
        self._now_utc_provider = now_utc_provider or (lambda: datetime.now(timezone.utc))

    async def get_candidate_slots_for_date(
        self,
        specialist_id: UUID,
        target_date_local_client: date,
        client_tz: str,
    ) -> dict[str, list[datetime]]:
        specialist_tz = await self._repository.get_specialist_timezone(specialist_id)
        target_date_local_specialist = self._to_specialist_local_date(
            target_date_local_client=target_date_local_client,
            client_tz=client_tz,
            specialist_tz=specialist_tz,
        )

        context = await self._repository.get_context_for_date(specialist_id, target_date_local_specialist)

        merged_intervals = merge_intervals(context.intervals)
        if not merged_intervals:
            return {"morning": [], "day": [], "evening": []}

        candidate_starts = self._build_candidates(
            target_date=target_date_local_specialist,
            intervals=merged_intervals,
            duration_min=context.session_duration_min,
            step_min=context.slot_step_min,
        )

        busy_intervals = await self._busy_provider.get_busy_for_local_day(
            specialist_id=specialist_id,
            specialist_tz=context.specialist_tz,
            target_date_local_specialist=target_date_local_specialist,
        )

        if len(busy_intervals) >= context.max_sessions_per_day:
            return {"morning": [], "day": [], "evening": []}

        min_start_utc = self._now_utc_provider() + timedelta(hours=context.cancel_window_hours)
        filtered = [
            start
            for start in candidate_starts
            if start.replace(tzinfo=ZoneInfo(context.specialist_tz)).astimezone(timezone.utc) >= min_start_utc
            and not self._overlaps_busy(start, context.session_duration_min, busy_intervals)
            and self._respects_buffer(start, context.session_duration_min, context.session_buffer_min, busy_intervals)
        ]

        return self._split_by_part_of_day(filtered)

    async def get_candidate_slots_for_date_range(
        self,
        *,
        specialist_id: UUID,
        target_date_local_client: date,
        client_tz: str,
        interval_start: time,
        interval_end: time,
    ) -> list[datetime]:
        specialist_tz = await self._repository.get_specialist_timezone(specialist_id)
        target_date_local_specialist = self._to_specialist_local_date(
            target_date_local_client=target_date_local_client,
            client_tz=client_tz,
            specialist_tz=specialist_tz,
        )

        context = await self._repository.get_context_for_date(specialist_id, target_date_local_specialist)
        if interval_start >= interval_end:
            return []

        interval_start_dt = datetime.combine(target_date_local_specialist, interval_start)
        interval_end_dt = datetime.combine(target_date_local_specialist, interval_end)

        candidate_starts = self._build_candidates(
            target_date=target_date_local_specialist,
            intervals=[(interval_start, interval_end)],
            duration_min=context.session_duration_min,
            step_min=context.slot_step_min,
        )

        busy_intervals = await self._busy_provider.get_busy_for_local_day(
            specialist_id=specialist_id,
            specialist_tz=context.specialist_tz,
            target_date_local_specialist=target_date_local_specialist,
        )

        if len(busy_intervals) >= context.max_sessions_per_day:
            return []

        min_start_utc = self._now_utc_provider() + timedelta(hours=context.cancel_window_hours)
        filtered = [
            start
            for start in candidate_starts
            if start.replace(tzinfo=ZoneInfo(context.specialist_tz)).astimezone(timezone.utc) >= min_start_utc
            and not self._overlaps_busy(start, context.session_duration_min, busy_intervals)
            and self._respects_buffer(start, context.session_duration_min, context.session_buffer_min, busy_intervals)
        ]

        confirmed_in_interval = [
            (busy_start, busy_end)
            for busy_start, busy_end in busy_intervals
            if busy_start < interval_end_dt and busy_end > interval_start_dt
        ]

        return rank_slots_for_interval(
            interval_start=interval_start_dt,
            interval_end=interval_end_dt,
            candidate_starts=filtered,
            existing_confirmed_sessions=confirmed_in_interval,
            session_duration=context.session_duration_min,
            buffer_minutes=context.session_buffer_min,
            max_results=6,
        )

    @staticmethod
    def _to_specialist_local_date(*, target_date_local_client: date, client_tz: str, specialist_tz: str) -> date:
        client_dt = datetime.combine(target_date_local_client, time(0, 0), tzinfo=ZoneInfo(client_tz))
        return client_dt.astimezone(ZoneInfo(specialist_tz)).date()

    @staticmethod
    def _build_candidates(
        *,
        target_date: date,
        intervals: list[tuple[time, time]],
        duration_min: int,
        step_min: int,
    ) -> list[datetime]:
        candidates: list[datetime] = []
        seen: set[datetime] = set()
        for start_time, end_time in intervals:
            interval_start = datetime.combine(target_date, start_time)
            interval_end = datetime.combine(target_date, end_time)
            for start in iter_slot_starts(
                interval_start,
                interval_end,
                step_min=step_min,
                duration_min=duration_min,
            ):
                if start in seen:
                    continue
                seen.add(start)
                candidates.append(start)
        return candidates

    @staticmethod
    def _overlaps_busy(start: datetime, duration_min: int, busy_intervals: list[tuple[datetime, datetime]]) -> bool:
        end = start + timedelta(minutes=duration_min)
        return any(start < busy_end and end > busy_start for busy_start, busy_end in busy_intervals)

    @staticmethod
    def _respects_buffer(
        start: datetime,
        duration_min: int,
        buffer_min: int,
        busy_intervals: list[tuple[datetime, datetime]],
    ) -> bool:
        end = start + timedelta(minutes=duration_min)
        buffer_delta = timedelta(minutes=max(buffer_min, 0))
        return all(
            (end + buffer_delta <= busy_start) or (start >= busy_end + buffer_delta)
            for busy_start, busy_end in busy_intervals
        )

    @staticmethod
    def _split_by_part_of_day(starts: list[datetime]) -> dict[str, list[datetime]]:
        result: dict[str, list[datetime]] = {"morning": [], "day": [], "evening": []}
        for start in sorted(starts):
            if start.hour < 13:
                result["morning"].append(start)
            elif start.hour < 17:
                result["day"].append(start)
            else:
                result["evening"].append(start)
        return result
