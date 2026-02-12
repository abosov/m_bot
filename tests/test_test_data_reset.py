import json
import importlib
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

pytest.importorskip("aiosqlite")


def load_modules(tmp_path, monkeypatch):
    db_path = tmp_path / "test_data_reset.db"
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
    import services.test_data_reset as test_data_reset
    import services.test_data_snapshot as test_data_snapshot

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(test_data_reset)
    importlib.reload(test_data_snapshot)
    return database, test_data_reset, test_data_snapshot


async def seed_data(database):
    specialist_target = uuid.uuid4()
    specialist_other = uuid.uuid4()

    target_client_1 = uuid.uuid4()
    target_client_2 = uuid.uuid4()
    other_client = uuid.uuid4()

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_target, status=database.SpecialistStatus.active),
                database.Specialist(specialist_id=specialist_other, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_target,
                    public_name="Smoke Specialist",
                    owner_tg_user_id=111,
                    owner_tg_username="smoke_owner",
                    specialist_timezone="UTC",
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_other,
                    public_name="Prod Specialist",
                    owner_tg_user_id=999,
                    owner_tg_username="prod_owner",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_target,
                    tg_user_id=111,
                ),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_other,
                    tg_user_id=999,
                ),
                database.Client(
                    client_id=target_client_1,
                    specialist_id=specialist_target,
                    tg_user_id=222,
                    tg_username="smoke_client_1",
                    display_name="Smoke Client 1",
                    client_code="A1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.client_selected,
                ),
                database.Client(
                    client_id=target_client_2,
                    specialist_id=specialist_target,
                    tg_user_id=223,
                    tg_username="smoke_client_2",
                    display_name="Smoke Client 2",
                    client_code="A2",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.client_selected,
                ),
                database.Client(
                    client_id=other_client,
                    specialist_id=specialist_other,
                    tg_user_id=888,
                    tg_username="prod_client",
                    display_name="Prod Client",
                    client_code="P1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.client_selected,
                ),
                database.Appointment(
                    specialist_id=specialist_target,
                    client_id=target_client_1,
                    start_at_utc=now,
                    end_at_utc=now,
                    booking_state=database.BookingState.confirmed,
                    idempotency_key="smoke-1",
                ),
                database.Appointment(
                    specialist_id=specialist_target,
                    client_id=target_client_2,
                    start_at_utc=now,
                    end_at_utc=now,
                    booking_state=database.BookingState.confirmed,
                    idempotency_key="smoke-2",
                ),
                database.Appointment(
                    specialist_id=specialist_other,
                    client_id=other_client,
                    start_at_utc=now,
                    end_at_utc=now,
                    booking_state=database.BookingState.confirmed,
                    idempotency_key="prod-1",
                ),
                database.WeeklyAvailability(
                    specialist_id=specialist_target,
                    weekday=1,
                    is_working=True,
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_target,
                    calendar_id="smoke-cal",
                    calendar_summary="Smoke",
                    calendar_time_zone="UTC",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.GoogleOAuth(
                    specialist_id=specialist_target,
                    refresh_token_encrypted="enc",
                    scopes="scope",
                    status=database.GoogleOAuthStatus.connected,
                    token_updated_at=now,
                ),
                database.OAuthState(
                    state="state-1",
                    type=database.OAuthStateType.google_connect,
                    specialist_id=specialist_target,
                    expires_at=now,
                ),
                database.TelegramBot(
                    specialist_id=specialist_target,
                    bot_token_encrypted="enc",
                    bot_user_id=10001,
                    bot_username="smoke_bot",
                    bot_name="Smoke Bot",
                    webhook_secret="secret",
                    webhook_url="https://example.com/hook",
                    status=database.TelegramBotStatus.active,
                ),
                database.MessageLog(
                    specialist_id=specialist_target,
                    bot_id=10001,
                    tg_user_id=111,
                    direction=database.LogDirection.IN,
                    message_type="message",
                ),
                database.MessageLog(
                    specialist_id=specialist_other,
                    bot_id=20001,
                    tg_user_id=888,
                    direction=database.LogDirection.IN,
                    message_type="message",
                ),
                database.BotHealthCheck(
                    specialist_id=specialist_target,
                    bot_user_id=10001,
                    status=database.BotHealthCheckStatus.ok,
                    latency_ms=50,
                ),
                database.BotHealthCheck(
                    specialist_id=specialist_other,
                    bot_user_id=20001,
                    status=database.BotHealthCheckStatus.ok,
                    latency_ms=50,
                ),
            ]
        )
        await session.commit()

    return {
        "specialist_target": specialist_target,
        "specialist_other": specialist_other,
    }


@pytest.mark.asyncio
async def test_cleanup_dry_run_keeps_rows(tmp_path, monkeypatch):
    database, test_data_reset, _ = load_modules(tmp_path, monkeypatch)
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    await seed_data(database)

    registry_path = tmp_path / "test_accounts.yaml"
    registry_path.write_text(
        json.dumps(
            {
                "accounts": [
                    {"name": "smoke_specialist_1", "role": "specialist_owner", "tg_user_id": 111},
                    {"name": "smoke_client_1", "role": "client", "tg_user_id": 222},
                    {"name": "smoke_client_2", "role": "client", "tg_user_id": 223},
                ],
                "notes": "test",
            }
        ),
        encoding="utf-8",
    )

    report = await test_data_reset.execute_test_data_reset(
        session_factory=database.async_session_factory,
        dry_run=True,
        registry_path=registry_path,
    )

    assert report["counts"]["specialist"] == 1
    assert report["counts"]["client"] == 2
    assert report["counts"]["appointment"] == 2

    async with database.async_session_factory() as session:
        specialist_count = await session.scalar(
            select(func.count()).select_from(database.Specialist)
        )
        assert specialist_count == 2


@pytest.mark.asyncio
async def test_cleanup_apply_deletes_only_target_scope(tmp_path, monkeypatch):
    database, test_data_reset, _ = load_modules(tmp_path, monkeypatch)
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    seeded = await seed_data(database)

    registry_path = tmp_path / "test_accounts.yaml"
    registry_path.write_text(
        json.dumps(
            {
                "accounts": [
                    {"name": "smoke_specialist_1", "role": "specialist_owner", "tg_user_id": 111},
                    {"name": "smoke_client_1", "role": "client", "tg_user_id": 222},
                    {"name": "smoke_client_2", "role": "client", "tg_user_id": 223},
                ],
                "notes": "test",
            }
        ),
        encoding="utf-8",
    )

    report = await test_data_reset.execute_test_data_reset(
        session_factory=database.async_session_factory,
        dry_run=False,
        registry_path=registry_path,
    )

    assert report["deleted_counts"]["specialist"] == 1
    assert report["deleted_counts"]["client"] == 2
    assert report["deleted_counts"]["appointment"] == 2

    async with database.async_session_factory() as session:
        target_exists = await session.scalar(
            select(database.Specialist.specialist_id).where(
                database.Specialist.specialist_id == seeded["specialist_target"]
            )
        )
        other_exists = await session.scalar(
            select(database.Specialist.specialist_id).where(
                database.Specialist.specialist_id == seeded["specialist_other"]
            )
        )
        other_clients = await session.scalar(
            select(func.count()).select_from(database.Client).where(
                database.Client.specialist_id == seeded["specialist_other"]
            )
        )

    assert target_exists is None
    assert other_exists == seeded["specialist_other"]
    assert other_clients == 1


@pytest.mark.asyncio
async def test_snapshot_restore_keeps_original_uuids(tmp_path, monkeypatch):
    database, _, test_data_snapshot = load_modules(tmp_path, monkeypatch)
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    seeded = await seed_data(database)

    registry_path = tmp_path / "test_accounts.yaml"
    registry_path.write_text(
        json.dumps(
            {
                "accounts": [
                    {"name": "smoke_specialist_1", "role": "specialist_owner", "tg_user_id": 111},
                    {"name": "smoke_client_1", "role": "client", "tg_user_id": 222},
                    {"name": "smoke_client_2", "role": "client", "tg_user_id": 223},
                ],
                "notes": "test",
            }
        ),
        encoding="utf-8",
    )

    save_report = await test_data_snapshot.create_test_data_snapshot(
        session_factory=database.async_session_factory,
        baseline_name="baseline_smoke",
        registry_path=registry_path,
    )
    assert save_report["table_counts"]["specialist"] == 1
    assert save_report["table_counts"]["client"] == 2

    restore_report = await test_data_snapshot.restore_test_data_snapshot(
        session_factory=database.async_session_factory,
        baseline_name="baseline_smoke",
        registry_path=registry_path,
    )
    assert restore_report["restored_counts"]["specialist"] == 1

    async with database.async_session_factory() as session:
        target_exists = await session.scalar(
            select(database.Specialist.specialist_id).where(
                database.Specialist.specialist_id == seeded["specialist_target"]
            )
        )
        other_exists = await session.scalar(
            select(database.Specialist.specialist_id).where(
                database.Specialist.specialist_id == seeded["specialist_other"]
            )
        )
        clients = (
            await session.execute(
                select(database.Client.client_id).where(
                    database.Client.specialist_id == seeded["specialist_target"]
                )
            )
        ).scalars().all()

    assert target_exists == seeded["specialist_target"]
    assert other_exists == seeded["specialist_other"]
    assert len(clients) == 2


@pytest.mark.asyncio
async def test_cleanup_safety_guard_threshold_requires_force(tmp_path, monkeypatch):
    database, test_data_reset, _ = load_modules(tmp_path, monkeypatch)
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    await seed_data(database)

    registry_path = tmp_path / "test_accounts.yaml"
    registry_path.write_text(
        json.dumps(
            {
                "accounts": [
                    {"name": "smoke_specialist_1", "role": "specialist_owner", "tg_user_id": 111},
                ],
                "notes": "threshold test",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(test_data_reset.TestDataResetError):
        await test_data_reset.execute_test_data_reset(
            session_factory=database.async_session_factory,
            dry_run=False,
            registry_path=registry_path,
            max_clients_threshold=1,
        )
