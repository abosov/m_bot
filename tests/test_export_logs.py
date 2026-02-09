import importlib
from datetime import datetime, timedelta, timezone
import uuid

import pytest

pytest.importorskip("aiosqlite")


def setup_modules(tmp_path, monkeypatch):
    db_path = tmp_path / "export_logs.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    import config
    import database
    import services.log_exporter as log_exporter

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(log_exporter)
    return database, log_exporter


@pytest.mark.asyncio
async def test_export_logs_jsonl_and_filters(tmp_path, monkeypatch):
    database, log_exporter = setup_modules(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    specialist_id = uuid.uuid4()

    log_ok = database.MessageLog(
        created_at=now - timedelta(minutes=5),
        specialist_id=specialist_id,
        bot_id=123,
        tg_user_id=999,
        direction=database.LogDirection.IN,
        message_type="message",
        content="Email a@example.com and phone +12345678901",
        fsm_state="state_a",
        handler_name="handler_a",
        processing_time=0.12,
        is_error=False,
    )
    log_error = database.MessageLog(
        created_at=now - timedelta(minutes=1),
        specialist_id=specialist_id,
        bot_id=123,
        tg_user_id=999,
        direction=database.LogDirection.OUT,
        message_type="message",
        content="token=abcdef" + "1" * 40,
        fsm_state="state_b",
        handler_name="handler_b",
        processing_time=0.32,
        is_error=True,
        error_details="ValueError: boom\ntrace",
    )

    async with database.async_session_factory() as session:
        session.add_all([log_ok, log_error])
        await session.commit()

    records = await log_exporter.collect_logs(
        source="message_logs",
        since=now - timedelta(minutes=2),
        direction=database.LogDirection.OUT,
        redact=True,
    )
    assert len(records) == 1
    assert records[0]["direction"] == "OUT"
    assert records[0]["content"] == "[REDACTED]"
    assert records[0]["error_details"] == "ValueError: boom\ntrace"

    jsonl = log_exporter.render_jsonl(records)
    assert jsonl.count("\n") == 1
