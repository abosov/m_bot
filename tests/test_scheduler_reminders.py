import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytest.importorskip("aiosqlite")


async def _seed_appointment(database, session, *, start_at_utc: datetime, booking_state, suffix: str):
    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    specialist = database.Specialist(
        specialist_id=specialist_id,
        status=database.SpecialistStatus.active,
    )
    client = database.Client(
        client_id=client_id,
        specialist_id=specialist_id,
        tg_user_id=1000 + len(suffix),
        client_code=f"C{suffix}",
        client_timezone="UTC",
        timezone_source=database.ClientTimezoneSource.default_from_specialist,
    )
    appointment = database.Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=client_id,
        start_at_utc=start_at_utc,
        end_at_utc=start_at_utc + timedelta(hours=1),
        booking_state=booking_state,
        idempotency_key=f"idem-{suffix}",
    )
    session.add_all([specialist, client, appointment])
    await session.flush()
    return appointment_id


@pytest.mark.asyncio
async def test_scheduler_creates_24h_reminder_once(monkeypatch, tmp_path):
    db_path = tmp_path / "scheduler_once.db"
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")

    import database
    import services.scheduler as scheduler


    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now_utc = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler, "async_session_factory", session_factory)

    async with session_factory() as session:
        async with session.begin():
            await _seed_appointment(
                database,
                session,
                start_at_utc=now_utc + timedelta(hours=24),
                booking_state=database.BookingState.confirmed,
                suffix="01",
            )

    await scheduler.run_scheduler_reminder_scan(now_utc=now_utc)
    await scheduler.run_scheduler_reminder_scan(now_utc=now_utc)

    async with session_factory() as session:
        reminders_count = await session.scalar(select(func.count()).select_from(database.AppointmentReminder))
        events_count = await session.scalar(
            select(func.count()).select_from(database.OutboxEvent).where(
                database.OutboxEvent.event_type == "appointment_client_reminder_24h"
            )
        )

    assert reminders_count == 1
    assert events_count == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_skips_non_confirmed(monkeypatch, tmp_path):
    db_path = tmp_path / "scheduler_non_confirmed.db"
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")

    import database
    import services.scheduler as scheduler


    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now_utc = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler, "async_session_factory", session_factory)

    async with session_factory() as session:
        async with session.begin():
            await _seed_appointment(
                database,
                session,
                start_at_utc=now_utc + timedelta(hours=24),
                booking_state=database.BookingState.pending,
                suffix="02",
            )
            await _seed_appointment(
                database,
                session,
                start_at_utc=now_utc + timedelta(hours=24),
                booking_state=database.BookingState.awaiting_specialist_confirmation,
                suffix="03",
            )

    await scheduler.run_scheduler_reminder_scan(now_utc=now_utc)

    async with session_factory() as session:
        reminders_count = await session.scalar(select(func.count()).select_from(database.AppointmentReminder))
        events_count = await session.scalar(select(func.count()).select_from(database.OutboxEvent))

    assert reminders_count == 0
    assert events_count == 0
    await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_window_includes_boundary(monkeypatch, tmp_path):
    db_path = tmp_path / "scheduler_boundary.db"
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")

    import database
    import services.scheduler as scheduler


    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now_utc = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(scheduler, "async_session_factory", session_factory)

    async with session_factory() as session:
        async with session.begin():
            await _seed_appointment(
                database,
                session,
                start_at_utc=now_utc + timedelta(hours=24) + scheduler.REMINDER_WINDOW_DELTA,
                booking_state=database.BookingState.confirmed,
                suffix="04",
            )

    await scheduler.run_scheduler_reminder_scan(now_utc=now_utc)

    async with session_factory() as session:
        reminders_count = await session.scalar(select(func.count()).select_from(database.AppointmentReminder))
        events = (
            await session.execute(
                select(database.OutboxEvent).where(
                    database.OutboxEvent.event_type == "appointment_client_reminder_24h"
                )
            )
        ).scalars().all()

    assert reminders_count == 1
    assert len(events) == 1
    await engine.dispose()
