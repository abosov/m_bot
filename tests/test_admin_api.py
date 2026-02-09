import importlib
from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
import pytest

pytest.importorskip("aiosqlite")


def load_app(tmp_path, monkeypatch, admin_key: str | None):
    db_path = tmp_path / "admin_api.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    if admin_key:
        monkeypatch.setenv("ADMIN_API_KEY", admin_key)
    else:
        monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    import config
    import database
    import admin_api
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(admin_api)
    importlib.reload(web_server)
    return web_server.app, database


@pytest.mark.asyncio
async def test_admin_logs_requires_key(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None)
    client = TestClient(app)
    response = client.get("/admin/logs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_logs_success_and_limit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    specialist_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.MessageLog(
                    created_at=now,
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=200,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="hi",
                ),
                database.MessageLog(
                    created_at=now,
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=200,
                    direction=database.LogDirection.OUT,
                    message_type="message",
                    content="ok",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/logs?limit=1000", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 500
    assert len(payload["items"]) == 2

    response_no_key = client.get("/admin/logs")
    assert response_no_key.status_code == 403
