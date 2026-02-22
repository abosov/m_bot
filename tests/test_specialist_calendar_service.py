import importlib
import uuid
from datetime import datetime, timezone

import pytest

pytest.importorskip("aiosqlite")


def _load_modules(tmp_path, monkeypatch):
    db_path = tmp_path / "specialist_calendar.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import config
    import database
    import services.specialist_calendar as specialist_calendar

    importlib.reload(config)
    importlib.reload(database)
    specialist_calendar = importlib.reload(specialist_calendar)
    return database, specialist_calendar


@pytest.mark.asyncio
async def test_set_specialist_calendar_smoke_failed_keeps_calendar_and_status(tmp_path, monkeypatch):
    database, specialist_calendar = _load_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="UTC",
            )
        )
        session.add(
            database.TelegramBot(
                specialist_id=specialist_id,
                bot_user_id=987654321,
                bot_username="spec_bot",
                bot_name="Spec Bot",
                bot_token_encrypted="enc",
                webhook_secret="secret",
                webhook_url="https://example.com/webhook",
                status=database.TelegramBotStatus.active,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    monkeypatch.setattr(specialist_calendar, "async_session_factory", database.async_session_factory)

    async def _access_ok(*args, **kwargs):
        return True

    async def _calendar_payload(*args, **kwargs):
        return {"summary": "Work", "timeZone": "Europe/Moscow"}

    async def _smoke_fail(*args, **kwargs):
        raise RuntimeError("integration broken")

    sent_messages = []

    class _BotStub:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent_messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})

    async def _bot_factory(_row):
        return _BotStub()

    monkeypatch.setattr(specialist_calendar, "ensure_calendar_access", _access_ok)
    monkeypatch.setattr(specialist_calendar, "get_calendar", _calendar_payload)
    monkeypatch.setattr(specialist_calendar, "create_and_cleanup_test_event", _smoke_fail)
    monkeypatch.setattr(specialist_calendar, "get_personal_bot", _bot_factory)

    status = await specialist_calendar.set_specialist_calendar(specialist_id, "cal-1")

    assert status == "failed"
    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == 777

    async with database.async_session_factory() as session:
        settings = await session.get(database.SpecialistCalendarSettings, specialist_id)
        sync_state = await session.get(
            database.CalendarSyncState,
            {"specialist_id": specialist_id, "calendar_id": "cal-1"},
        )

    assert settings is not None
    assert settings.calendar_id == "cal-1"
    assert settings.last_smoke_test_status == "failed"
    assert settings.last_smoke_test_error == "integration broken"

    assert sync_state is not None
    assert sync_state.calendar_id == "cal-1"
    assert sync_state.last_error_at is not None
    assert sync_state.error_count == 1


@pytest.mark.asyncio
async def test_set_specialist_calendar_empty_id_returns_failed(tmp_path, monkeypatch):
    _, specialist_calendar = _load_modules(tmp_path, monkeypatch)

    status = await specialist_calendar.set_specialist_calendar(uuid.uuid4(), "   ")

    assert status == "failed"
