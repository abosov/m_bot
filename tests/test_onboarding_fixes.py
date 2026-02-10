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
