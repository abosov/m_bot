from __future__ import annotations

from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database import SpecialistWorkingInterval, async_session_factory

WorkingIntervalPair = tuple[int | None, int | None]
WorkingIntervalsByIdx = dict[int, WorkingIntervalPair]


class WorkingIntervalsRepository:
    async def get_working_intervals(self, specialist_id: UUID) -> WorkingIntervalsByIdx:
        intervals: WorkingIntervalsByIdx = {
            1: (None, None),
            2: (None, None),
            3: (None, None),
        }

        async with async_session_factory() as session:
            rows = (
                await session.execute(
                    select(
                        SpecialistWorkingInterval.idx,
                        SpecialistWorkingInterval.start_min,
                        SpecialistWorkingInterval.end_min,
                    )
                    .where(SpecialistWorkingInterval.specialist_id == specialist_id)
                    .order_by(SpecialistWorkingInterval.idx.asc())
                )
            ).all()

        for idx, start_min, end_min in rows:
            intervals[idx] = (start_min, end_min)
        return intervals

    async def upsert_working_intervals(
        self,
        specialist_id: UUID,
        intervals_dict: Mapping[int, WorkingIntervalPair],
    ) -> None:
        payload = [
            {
                "specialist_id": specialist_id,
                "idx": idx,
                "start_min": intervals_dict.get(idx, (None, None))[0],
                "end_min": intervals_dict.get(idx, (None, None))[1],
            }
            for idx in (1, 2, 3)
        ]

        stmt = insert(SpecialistWorkingInterval).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                SpecialistWorkingInterval.specialist_id,
                SpecialistWorkingInterval.idx,
            ],
            set_={
                "start_min": stmt.excluded.start_min,
                "end_min": stmt.excluded.end_min,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        async with async_session_factory() as session:
            await session.execute(stmt)
            await session.commit()
