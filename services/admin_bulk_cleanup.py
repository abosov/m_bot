from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from database import AdminBulkCleanupJob, Specialist, async_session_factory

DeleteSpecialistFn = Callable[[uuid.UUID], Awaitable[None]]


async def run_admin_bulk_cleanup_job(
    job_id: uuid.UUID,
    *,
    delete_specialist_fn: DeleteSpecialistFn,
    max_retries: int = 1,
) -> AdminBulkCleanupJob:
    async with async_session_factory() as session:
        job = await session.get(AdminBulkCleanupJob, job_id)
        if job is None:
            raise ValueError("job_not_found")

        specialist_ids = list(
            (
                await session.execute(
                    select(Specialist.specialist_id)
                    .where(Specialist.is_test.is_(True), Specialist.is_system.is_(False))
                    .order_by(Specialist.created_at.asc())
                )
            ).scalars()
        )

        job.status = "running"
        job.total_specialists = len(specialist_ids)
        job.processed_specialists = 0
        job.error_count = 0
        await session.commit()

        for specialist_id in specialist_ids:
            attempt = 0
            success = False
            while attempt <= max_retries:
                try:
                    await delete_specialist_fn(specialist_id)
                    success = True
                    break
                except Exception:
                    attempt += 1

            job.processed_specialists += 1
            if not success:
                job.error_count += 1
            await session.commit()

        if job.total_specialists == 0:
            job.status = "completed"
        elif job.error_count == 0:
            job.status = "completed"
        elif job.error_count < job.total_specialists:
            job.status = "partial"
        else:
            job.status = "failed"

        await session.commit()
        await session.refresh(job)
        return job
