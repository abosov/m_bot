import importlib
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytest.importorskip("aiosqlite")


@pytest.mark.asyncio
async def test_appointment_reminder_unique_constraint(monkeypatch, tmp_path):
    db_path = tmp_path / "appointment_reminder.db"
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")

    import database

    database = importlib.reload(database)

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    client_id = uuid.uuid4()
    appointment_id = uuid.uuid4()

    async with session_factory() as session:
        specialist = database.Specialist(
            specialist_id=specialist_id,
            status=database.SpecialistStatus.active,
        )
        client = database.Client(
            client_id=client_id,
            specialist_id=specialist_id,
            tg_user_id=123456,
            client_code="C001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        appointment = database.Appointment(
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            client_id=client_id,
            start_at_utc=datetime.now(timezone.utc) + timedelta(days=2),
            end_at_utc=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
            booking_state=database.BookingState.confirmed,
            idempotency_key="idem-1",
        )

        session.add_all([specialist, client, appointment])
        await session.commit()

    async with session_factory() as session:
        first = database.AppointmentReminder(
            id=uuid.uuid4(),
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            reminder_type=database.ReminderType.h24,
            due_at_utc=datetime.now(timezone.utc) + timedelta(days=1),
            created_at_utc=datetime.now(timezone.utc),
        )
        duplicate = database.AppointmentReminder(
            id=uuid.uuid4(),
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            reminder_type=database.ReminderType.h24,
            due_at_utc=datetime.now(timezone.utc) + timedelta(days=1),
            created_at_utc=datetime.now(timezone.utc),
        )

        session.add(first)
        await session.commit()

        session.add(duplicate)
        with pytest.raises(IntegrityError):
            await session.commit()

    await engine.dispose()
