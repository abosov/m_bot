import importlib
import uuid

import pytest

pytest.importorskip("aiosqlite")


def load_modules(tmp_path, monkeypatch):
    db_path = tmp_path / "bulk_cleanup.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")

    import config
    import database
    import services.admin_bulk_cleanup as admin_bulk_cleanup

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(admin_bulk_cleanup)
    return database, admin_bulk_cleanup


@pytest.mark.asyncio
async def test_bulk_job_created(tmp_path, monkeypatch):
    database, _admin_bulk_cleanup = load_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    job_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.AdminBulkCleanupJob(job_id=job_id, status="pending"))
        await session.commit()

    async with database.async_session_factory() as session:
        job = await session.get(database.AdminBulkCleanupJob, job_id)

    assert job is not None
    assert job.status == "pending"


@pytest.mark.asyncio
async def test_worker_processes_specialists_and_updates_completed_status(tmp_path, monkeypatch):
    database, admin_bulk_cleanup = load_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    job_id = uuid.uuid4()
    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()
    deleted: list[uuid.UUID] = []

    async with database.async_session_factory() as session:
        session.add(database.AdminBulkCleanupJob(job_id=job_id, status="pending"))
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_a, status=database.SpecialistStatus.active, is_test=True, is_system=False),
                database.Specialist(specialist_id=specialist_b, status=database.SpecialistStatus.active, is_test=True, is_system=False),
            ]
        )
        await session.commit()

    async def _delete_stub(specialist_id: uuid.UUID):
        deleted.append(specialist_id)

    job = await admin_bulk_cleanup.run_admin_bulk_cleanup_job(job_id, delete_specialist_fn=_delete_stub)

    assert deleted == [specialist_a, specialist_b]
    assert job.total_specialists == 2
    assert job.processed_specialists == 2
    assert job.error_count == 0
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_retry_works_for_transient_failure(tmp_path, monkeypatch):
    database, admin_bulk_cleanup = load_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    job_id = uuid.uuid4()
    specialist_id = uuid.uuid4()
    attempts = {specialist_id: 0}

    async with database.async_session_factory() as session:
        session.add(database.AdminBulkCleanupJob(job_id=job_id, status="pending"))
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=True,
                is_system=False,
            )
        )
        await session.commit()

    async def _delete_flaky(spec_id: uuid.UUID):
        attempts[spec_id] += 1
        if attempts[spec_id] == 1:
            raise RuntimeError("transient")

    job = await admin_bulk_cleanup.run_admin_bulk_cleanup_job(
        job_id,
        delete_specialist_fn=_delete_flaky,
        max_retries=1,
    )

    assert attempts[specialist_id] == 2
    assert job.processed_specialists == 1
    assert job.error_count == 0
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_job_status_updates_to_partial_and_failed(tmp_path, monkeypatch):
    database, admin_bulk_cleanup = load_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    partial_job_id = uuid.uuid4()
    failed_job_id = uuid.uuid4()

    partial_ok = uuid.uuid4()
    partial_fail = uuid.uuid4()
    failed_a = uuid.uuid4()
    failed_b = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.AdminBulkCleanupJob(job_id=partial_job_id, status="pending"),
                database.AdminBulkCleanupJob(job_id=failed_job_id, status="pending"),
                database.Specialist(specialist_id=partial_ok, status=database.SpecialistStatus.active, is_test=True, is_system=False),
                database.Specialist(specialist_id=partial_fail, status=database.SpecialistStatus.active, is_test=True, is_system=False),
                database.Specialist(specialist_id=failed_a, status=database.SpecialistStatus.active, is_test=True, is_system=False),
                database.Specialist(specialist_id=failed_b, status=database.SpecialistStatus.active, is_test=True, is_system=False),
            ]
        )
        await session.commit()

    async def _delete_partial(spec_id: uuid.UUID):
        if spec_id in {partial_fail, failed_a, failed_b}:
            raise RuntimeError("boom")

    partial_job = await admin_bulk_cleanup.run_admin_bulk_cleanup_job(
        partial_job_id,
        delete_specialist_fn=_delete_partial,
        max_retries=0,
    )

    assert partial_job.status == "partial"
    assert partial_job.error_count > 0
    assert partial_job.processed_specialists == partial_job.total_specialists

    async def _delete_all_fail(_spec_id: uuid.UUID):
        raise RuntimeError("always-fail")

    failed_job = await admin_bulk_cleanup.run_admin_bulk_cleanup_job(
        failed_job_id,
        delete_specialist_fn=_delete_all_fail,
        max_retries=0,
    )

    assert failed_job.status == "failed"
    assert failed_job.error_count == failed_job.total_specialists
