import asyncio
import importlib
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import select

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

    state_value = "state-valid-existing-token"

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
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        return (None, "access", 3600)

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)
    async def _fake_list_calendars(_sid):
        return []

    monkeypatch.setattr(web_server, "list_calendars", _fake_list_calendars)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=abc&state={state_value}")

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

    state_value = "state-valid-no-refresh"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        return (None, "access", 3600)

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=abc&state={state_value}")

    assert response.status_code == 200
    assert "Требуется переподключение" in response.text

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is None


@pytest.mark.asyncio
async def test_notify_personal_bot_welcome_picks_most_recent_active_bot(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add_all(
            [
                database.TelegramBot(
                    specialist_id=specialist_id,
                    bot_user_id=1001,
                    bot_username="older_bot",
                    bot_name="Older",
                    bot_token_encrypted="enc-older",
                    webhook_secret="secret-1",
                    webhook_url="https://example.com/1",
                    status=database.TelegramBotStatus.active,
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
                ),
                database.TelegramBot(
                    specialist_id=specialist_id,
                    bot_user_id=1002,
                    bot_username="newer_bot",
                    bot_name="Newer",
                    bot_token_encrypted="enc-newer",
                    webhook_secret="secret-2",
                    webhook_url="https://example.com/2",
                    status=database.TelegramBotStatus.active,
                    created_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
                    updated_at=datetime(2024, 1, 4, tzinfo=timezone.utc),
                ),
            ]
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)
    monkeypatch.setattr(onboarding, "decrypt_token", lambda token: f"decrypted::{token}")

    sent = []

    class _BotStub:
        def __init__(self, token, default):
            self.token = token
            self.default = default
            self.session = SimpleNamespace(close=self._close)

        async def send_message(self, chat_id, text, request_timeout):
            sent.append((self.token, chat_id, text, request_timeout))

        async def _close(self):
            return None

    monkeypatch.setattr(onboarding, "Bot", _BotStub)

    username = await onboarding._notify_personal_bot_welcome(specialist_id, tg_user_id=777)

    assert username == "newer_bot"
    assert sent == [
        ("decrypted::enc-newer", 777, "🎉 Личный бот готов к работе.", 6.0),
    ]


@pytest.mark.asyncio
async def test_notify_personal_bot_welcome_returns_username_on_send_error(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.TelegramBot(
                specialist_id=specialist_id,
                bot_user_id=2001,
                bot_username="error_bot",
                bot_name="Error",
                bot_token_encrypted="enc-error",
                webhook_secret="secret-err",
                webhook_url="https://example.com/err",
                status=database.TelegramBotStatus.active,
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)
    monkeypatch.setattr(onboarding, "decrypt_token", lambda token: f"decrypted::{token}")

    class _BotErrorStub:
        def __init__(self, token, default):
            self.session = SimpleNamespace(close=self._close)

        async def send_message(self, chat_id, text, request_timeout):
            raise onboarding.TelegramNetworkError(method="sendMessage", message="network down")

        async def _close(self):
            return None

    monkeypatch.setattr(onboarding, "Bot", _BotErrorStub)

    username = await onboarding._notify_personal_bot_welcome(specialist_id, tg_user_id=888)

    assert username == "error_bot"


@pytest.mark.asyncio
async def test_google_oauth_callback_valid_state_consumes_and_upserts_token(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    state_value = "state-valid-upsert"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        return ("refresh-1", "access", 3600)

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    async def _fake_list_calendars(_sid):
        return []

    monkeypatch.setattr(web_server, "list_calendars", _fake_list_calendars)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert response.status_code == 200
    assert "Успешно" in response.text

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is not None
        assert oauth.status == database.GoogleOAuthStatus.connected

        state_entry = (
            await session.execute(
                select(database.OAuthState).where(database.OAuthState.state == state_value)
            )
        ).scalar_one_or_none()
        assert state_entry is None


@pytest.mark.asyncio
async def test_google_oauth_callback_expired_state_rejected(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    state_value = "state-expired"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        await session.commit()

    called = {"value": False}

    async def _fake_exchange(_code):
        called["value"] = True
        return ("refresh", "access", 3600)

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert response.status_code == 200
    assert "state истёк" in response.text
    assert called["value"] is False


@pytest.mark.asyncio
async def test_google_oauth_callback_reused_state_rejected_on_second_call(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    state_value = "state-reused"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        return ("refresh-1", "access", 3600)

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    async def _fake_list_calendars(_sid):
        return []

    monkeypatch.setattr(web_server, "list_calendars", _fake_list_calendars)

    client = TestClient(web_server.app)
    first = client.get(f"/google/oauth/callback?code=fake&state={state_value}")
    second = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert first.status_code == 200
    assert "Успешно" in first.text
    assert second.status_code == 200
    assert "state не найден или уже использован" in second.text


@pytest.mark.asyncio
async def test_google_oauth_callback_token_exchange_timeout_returns_timeout_html(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    state_value = "state-timeout"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert response.status_code == 200
    assert "timeout" in response.text.lower()


@pytest.mark.asyncio
async def test_google_oauth_callback_token_exchange_network_error_returns_network_html(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    state_value = "state-network"

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.OAuthState(
                state=state_value,
                specialist_id=specialist_id,
                type=database.OAuthStateType.google_connect,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
        await session.commit()

    async def _fake_exchange(_code):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(web_server, "exchange_code_for_token_async", _fake_exchange)

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert response.status_code == 200
    assert "network error" in response.text.lower()
