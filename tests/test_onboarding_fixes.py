import importlib
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("aiosqlite")


@pytest.mark.parametrize(
    ("existing_specialist", "current_specialist", "expected"),
    [
        (None, uuid.uuid4(), "create"),
        ("same", "same", "update"),
        ("owner", "requester", "blocked"),
    ],
)
def test_resolve_bot_registration_action(existing_specialist, current_specialist, expected, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import handlers.master_onboarding as onboarding

    if existing_specialist is None:
        existing_bot = None
        current_id = current_specialist
    else:
        existing_bot = SimpleNamespace(specialist_id=existing_specialist)
        current_id = current_specialist

    assert onboarding._resolve_bot_registration_action(existing_bot, current_id) == expected


def _load_web_app(tmp_path, monkeypatch):
    db_path = tmp_path / "oauth_callback.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "invalid-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")

    import config
    import database
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(web_server)
    return web_server, database


@pytest.mark.asyncio
async def test_google_oauth_callback_without_refresh_uses_existing_token(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    encrypted = "already-encrypted-token"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted=encrypted,
                scopes="old",
                status=database.GoogleOAuthStatus.error,
                token_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    monkeypatch.setattr(web_server, "exchange_code_for_token", lambda _code: (None, "access", 3600))
    async def _fake_list_calendars(_sid):
        return []

    monkeypatch.setattr(web_server, "list_calendars", _fake_list_calendars)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=abc&state={specialist_id}")

    assert response.status_code == 200
    assert "Успешно" in response.text

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is not None
        assert oauth.refresh_token_encrypted == encrypted
        assert oauth.status == database.GoogleOAuthStatus.connected


@pytest.mark.asyncio
async def test_google_oauth_callback_without_refresh_and_no_saved_token_marks_error_flow(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        await session.commit()

    monkeypatch.setattr(web_server, "exchange_code_for_token", lambda _code: (None, "access", 3600))

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=abc&state={specialist_id}")

    assert response.status_code == 200
    assert "Требуется переподключение" in response.text

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is None
