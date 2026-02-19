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
    response = client.get(f"/google/oauth/callback?code=abc&state={state_value}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost/success"

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

        async def send_message(self, chat_id, text, request_timeout=None, **kwargs):
            sent.append((self.token, chat_id, text, request_timeout, kwargs))

        async def _close(self):
            return None

    monkeypatch.setattr(onboarding, "Bot", _BotStub)

    username = await onboarding._notify_personal_bot_welcome(specialist_id, tg_user_id=777)

    assert username == "newer_bot"
    assert sent == [
        ("decrypted::enc-newer", 777, "🎉 Личный бот готов к работе.", 6.0, {}),
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

        async def send_message(self, chat_id, text, request_timeout=None, **kwargs):
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

    async with database.async_session_factory() as session:
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    sent = []

    class _BotStub:
        async def send_message(self, chat_id, text, **kwargs):
            sent.append({"chat_id": chat_id, "text": text, **kwargs})

    monkeypatch.setattr(web_server, "bot", _BotStub())

    client = TestClient(web_server.app)
    response = client.get(f"/google/oauth/callback?code=fake&state={state_value}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost/success"
    assert len(sent) == 1
    assert sent[0]["chat_id"] == 777
    keyboard = sent[0]["reply_markup"]
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "calendar:create" in callbacks
    assert "calendar:select" in callbacks

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
    first = client.get(f"/google/oauth/callback?code=fake&state={state_value}", follow_redirects=False)
    second = client.get(f"/google/oauth/callback?code=fake&state={state_value}")

    assert first.status_code == 302
    assert first.headers["location"] == "http://localhost/success"
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


def test_calendar_select_keyboard_and_text_navigation(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import handlers.master_onboarding as onboarding

    items = [
        {"id": f"cal-{i}", "summary": f"Calendar {i}", "timeZone": "UTC", "primary": False, "accessRole": "owner"}
        for i in range(7)
    ]

    kb_page0 = onboarding._calendar_select_keyboard(items, page=0, per_page=6)
    buttons0 = [btn for row in kb_page0.inline_keyboard for btn in row]
    assert any(btn.callback_data == "calendar:refresh" for btn in buttons0)
    assert any(btn.callback_data == "calendar:page:1" for btn in buttons0)
    assert not any(btn.callback_data == "calendar:page:-1" for btn in buttons0)
    assert any(btn.callback_data == "calendar:pick:0" for btn in buttons0)
    assert any(btn.callback_data == "calendar:pick:5" for btn in buttons0)

    kb_page1 = onboarding._calendar_select_keyboard(items, page=1, per_page=6)
    buttons1 = [btn for row in kb_page1.inline_keyboard for btn in row]
    assert any(btn.callback_data == "calendar:page:0" for btn in buttons1)
    assert any(btn.callback_data == "calendar:pick:6" for btn in buttons1)

    text = onboarding._calendar_select_text(total=7, page=1, per_page=6, has_readonly=True)
    assert "Zumbot подключается к уже существующему календарю Google" in text
    assert "Страница 2/2" in text
    assert "только для чтения" in text

    empty_text = onboarding._calendar_select_text(total=0, page=0, per_page=6, has_readonly=False)
    assert "Пока не удалось получить доступные календари" in empty_text

    kb_empty = onboarding._calendar_select_keyboard([], page=0, per_page=6)
    buttons_empty = [btn for row in kb_empty.inline_keyboard for btn in row]
    assert any(btn.callback_data == "calendar:refresh" for btn in buttons_empty)


@pytest.mark.asyncio
async def test_calendar_pick_success_sets_selected_and_smoke_ok(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    upsert_calls = []

    async def _upsert_stub(*args, **kwargs):
        upsert_calls.append(kwargs)

    async def _smoke_stub(specialist_id_arg, calendar_id_arg, tz_arg):
        assert specialist_id_arg == specialist_id
        assert calendar_id_arg == "cal-1"
        assert tz_arg == "Europe/Moscow"

    async def _finalize_stub(_sid):
        return None

    async def _welcome_stub(_sid, _tg_user_id):
        return "my_personal_bot"

    watch_calls = []

    async def _watch_stub(specialist_id_arg, calendar_id_arg):
        watch_calls.append((specialist_id_arg, calendar_id_arg))

    monkeypatch.setattr(onboarding, "_upsert_calendar_settings", _upsert_stub)
    monkeypatch.setattr(onboarding, "create_and_cleanup_test_event", _smoke_stub)
    monkeypatch.setattr(onboarding, "ensure_calendar_watch", _watch_stub)
    monkeypatch.setattr(onboarding, "finalize_specialist_if_ready", _finalize_stub)
    monkeypatch.setattr(onboarding, "_notify_personal_bot_welcome", _welcome_stub)

    class _State:
        async def get_data(self):
            return {
                "cal_items": [
                    {
                        "id": "cal-1",
                        "summary": "Work",
                        "timeZone": "Europe/Moscow",
                        "primary": False,
                        "accessRole": "owner",
                    }
                ]
            }

        async def clear(self):
            return None

    class _Message:
        def __init__(self):
            self.sent = []

        async def answer(self, text, reply_markup=None, **kwargs):
            self.sent.append((text, reply_markup, kwargs))

    class _Callback:
        def __init__(self):
            self.from_user = SimpleNamespace(id=777)
            self.data = "calendar:pick:0"
            self.message = _Message()

        async def answer(self, *args, **kwargs):
            return None

    callback = _Callback()
    await onboarding.calendar_pick(callback, _State())

    assert len(upsert_calls) == 2
    assert upsert_calls[0]["source"] == database.SpecialistCalendarSource.selected
    assert upsert_calls[1]["source"] == database.SpecialistCalendarSource.selected
    assert upsert_calls[1]["smoke_status"] == "ok"
    assert watch_calls == [(specialist_id, "cal-1")]


@pytest.mark.asyncio
async def test_send_safe_html_message_fallbacks_to_plain_text(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import handlers.master_onboarding as onboarding

    calls: list[dict] = []

    class _MessageStub:
        async def answer(self, text, parse_mode=None, reply_markup=None):
            calls.append({"text": text, "parse_mode": parse_mode, "reply_markup": reply_markup})
            if len(calls) == 1:
                raise onboarding.TelegramBadRequest(method="sendMessage", message="can't parse entities")
            return "ok"

    result = await onboarding._send_safe_html_message(_MessageStub(), "<b>hello</b>")

    assert result == "ok"
    assert len(calls) == 2
    assert calls[0]["parse_mode"] == onboarding.ParseMode.HTML
    assert calls[1]["parse_mode"] is None




@pytest.mark.asyncio
async def test_calendar_pick_success_message_falls_back_to_plain_text_on_bad_entities(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    async def _upsert_stub(*args, **kwargs):
        return None

    async def _smoke_stub(*args, **kwargs):
        return None

    async def _finalize_stub(*args, **kwargs):
        return None

    async def _welcome_stub(*args, **kwargs):
        return "my_personal_bot"

    monkeypatch.setattr(onboarding, "_upsert_calendar_settings", _upsert_stub)
    monkeypatch.setattr(onboarding, "create_and_cleanup_test_event", _smoke_stub)
    monkeypatch.setattr(onboarding, "finalize_specialist_if_ready", _finalize_stub)
    monkeypatch.setattr(onboarding, "_notify_personal_bot_welcome", _welcome_stub)

    class _State:
        async def get_data(self):
            return {
                "cal_items": [
                    {
                        "id": "cal-1",
                        "summary": "Work",
                        "timeZone": "Europe/Moscow",
                        "primary": False,
                        "accessRole": "owner",
                    }
                ]
            }

        async def clear(self):
            return None

    class _Message:
        def __init__(self):
            self.calls = []

        async def answer(self, text, parse_mode=None, disable_web_page_preview=None, reply_markup=None, **kwargs):
            self.calls.append(
                {
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": disable_web_page_preview,
                    "reply_markup": reply_markup,
                }
            )
            if len(self.calls) == 1:
                raise onboarding.TelegramBadRequest(method="sendMessage", message="can't parse entities")
            return None

    class _Callback:
        def __init__(self):
            self.from_user = SimpleNamespace(id=777)
            self.data = "calendar:pick:0"
            self.message = _Message()

        async def answer(self, *args, **kwargs):
            return None

    callback = _Callback()
    await onboarding.calendar_pick(callback, _State())

    assert len(callback.message.calls) == 2
    assert callback.message.calls[0]["parse_mode"] is None
    assert callback.message.calls[0]["disable_web_page_preview"] is True
    assert callback.message.calls[1]["parse_mode"] is None
    assert callback.message.calls[1]["disable_web_page_preview"] is None

@pytest.mark.asyncio
async def test_calendar_pick_post_success_exception_shows_final_step_warning(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    async def _upsert_fail(*args, **kwargs):
        raise RuntimeError("post-apply failed")

    async def _notify_exception_stub(**kwargs):
        return None

    monkeypatch.setattr(onboarding, "_upsert_calendar_settings", _upsert_fail)
    monkeypatch.setattr(onboarding, "notify_exception", _notify_exception_stub)

    class _State:
        async def get_data(self):
            return {
                "cal_items": [
                    {
                        "id": "cal-1",
                        "summary": "Work",
                        "timeZone": "Europe/Moscow",
                        "primary": False,
                        "accessRole": "owner",
                    }
                ]
            }

        async def clear(self):
            return None

    class _Message:
        def __init__(self):
            self.sent = []

        async def answer(self, text, reply_markup=None, **kwargs):
            self.sent.append((text, reply_markup, kwargs))

    class _Callback:
        def __init__(self):
            self.from_user = SimpleNamespace(id=777)
            self.data = "calendar:pick:0"
            self.message = _Message()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1
            return None

    callback = _Callback()
    await onboarding.calendar_pick(callback, _State())

    assert any("Календарь выбран/подключён" in text for text, _, _ in callback.message.sent)
    assert not any("Не удалось применить выбранный календарь" in text for text, _, _ in callback.message.sent)
    assert callback.answered == 1


@pytest.mark.asyncio
async def test_calendar_create_post_success_exception_shows_final_step_warning(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    async def _create_calendar_stub(*args, **kwargs):
        return {"id": "created-cal", "summary": "Spec", "timeZone": "Europe/Moscow"}

    async def _upsert_fail(*args, **kwargs):
        raise RuntimeError("persist failed")

    async def _notify_exception_stub(**kwargs):
        return None

    monkeypatch.setattr(onboarding, "create_bot_calendar", _create_calendar_stub)
    monkeypatch.setattr(onboarding, "_upsert_calendar_settings", _upsert_fail)
    monkeypatch.setattr(onboarding, "notify_exception", _notify_exception_stub)

    class _State:
        async def clear(self):
            return None

    class _Message:
        def __init__(self):
            self.sent = []

        async def answer(self, text, reply_markup=None, **kwargs):
            self.sent.append((text, reply_markup, kwargs))

    class _Callback:
        def __init__(self):
            self.from_user = SimpleNamespace(id=777)
            self.data = "calendar:create"
            self.message = _Message()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1
            return None

    callback = _Callback()
    await onboarding.calendar_create(callback, _State())

    assert any("Календарь создан/подключён" in text for text, _, _ in callback.message.sent)
    assert not any("Не удалось подключить календарь" in text for text, _, _ in callback.message.sent)
    assert callback.answered == 1


@pytest.mark.asyncio
async def test_calendar_create_uses_answer_plain_for_final_deep_link_message_to_avoid_parse_entities(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    async def _resolve_tz_stub(*args, **kwargs):
        return "Europe/Moscow"

    async def _create_calendar_stub(*args, **kwargs):
        return {"id": "created-cal", "summary": "Spec", "timeZone": "Europe/Moscow"}

    async def _noop_async(*args, **kwargs):
        return None

    async def _notify_bot_stub(*args, **kwargs):
        return "zumbot_personal_bot"

    def _build_link_stub(*args, **kwargs):
        return "https://t.me/zumbot_personal_bot?start=owner_panel"

    monkeypatch.setattr(onboarding, "resolve_tz_for_calendar_creation", _resolve_tz_stub)
    monkeypatch.setattr(onboarding, "create_bot_calendar", _create_calendar_stub)
    monkeypatch.setattr(onboarding, "apply_specialist_defaults_if_missing", _noop_async)
    monkeypatch.setattr(onboarding, "_upsert_calendar_settings", _noop_async)
    monkeypatch.setattr(onboarding, "create_and_cleanup_test_event", _noop_async)
    monkeypatch.setattr(onboarding, "finalize_specialist_if_ready", _noop_async)
    monkeypatch.setattr(onboarding, "_notify_personal_bot_welcome", _notify_bot_stub)
    monkeypatch.setattr(onboarding, "_build_personal_deep_link", _build_link_stub)

    class _State:
        async def clear(self):
            return None

    class _DummyMessage:
        def __init__(self):
            self.sent = []

        async def answer(self, text, **kwargs):
            self.sent.append((text, kwargs))

    class _DummyCallback:
        def __init__(self):
            self.from_user = SimpleNamespace(id=777)
            self.data = "calendar:create"
            self.message = _DummyMessage()
            self.answered = 0

        async def answer(self, *args, **kwargs):
            self.answered += 1
            return None

    callback = _DummyCallback()
    await onboarding.calendar_create(callback, _State())

    final_sent = [item for item in callback.message.sent if "Master-онбординг завершён" in item[0]]
    assert len(final_sent) == 1
    final_text, final_kwargs = final_sent[0]

    assert "@zumbot_personal_bot" in final_text
    assert "https://t.me/zumbot_personal_bot?start=owner_panel" in final_text
    assert final_kwargs.get("parse_mode") is None
    assert final_kwargs.get("disable_web_page_preview") is True
    assert callback.answered == 1

@pytest.mark.asyncio
async def test_process_bot_token_sends_connect_page_button_with_fragment_token(tmp_path, monkeypatch):
    _, database = _load_web_app(tmp_path, monkeypatch)

    import handlers.master_onboarding as onboarding

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding))
        session.add(
            database.SpecialistAuthTelegram(
                specialist_id=specialist_id,
                tg_user_id=777,
                tg_username="spec",
                tg_first_name="Spec",
                tg_last_name=None,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Spec",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    monkeypatch.setattr(onboarding, "async_session_factory", database.async_session_factory)

    async def _set_webhook_ok(*args, **kwargs):
        return None

    async def _noop_async(*args, **kwargs):
        return None

    async def _fake_create_connect_token(_db, _specialist_id, _tg_user_id, ttl_minutes=15):
        assert _specialist_id == specialist_id
        assert _tg_user_id == 777
        assert ttl_minutes == 15
        return "raw-test-token"

    monkeypatch.setattr(onboarding, "_set_webhook_with_retry", _set_webhook_ok)
    monkeypatch.setattr(onboarding, "set_master_onboarding_completed", _noop_async)
    monkeypatch.setattr(onboarding, "finalize_specialist_if_ready", _noop_async)
    monkeypatch.setattr(onboarding, "log_outbound_message", _noop_async)
    monkeypatch.setattr(onboarding.web_connect, "create_connect_token", _fake_create_connect_token)

    class _BotStub:
        def __init__(self, token, *args, **kwargs):
            self.token = token
            self.session = SimpleNamespace(close=self._close)

        async def get_me(self, request_timeout=None):
            return SimpleNamespace(id=100500, username="my_spec_bot", first_name="Spec Bot")

        async def _close(self):
            return None

    monkeypatch.setattr(onboarding, "Bot", _BotStub)

    class _State:
        async def get_state(self):
            return onboarding.OnboardingStates.waiting_for_bot_token.state

        async def clear(self):
            return None

        async def set_state(self, _state):
            return None

    class _Message:
        def __init__(self):
            self.text = "123456:validtoken"
            self.from_user = SimpleNamespace(id=777, username="spec", first_name="Spec", last_name=None)
            self.bot = object()
            self.sent = []

        async def answer(self, text, reply_markup=None, **kwargs):
            self.sent.append((text, reply_markup, kwargs))

    message = _Message()
    await onboarding.process_bot_token(message, _State())

    assert message.sent
    _, keyboard, _ = message.sent[-1]
    assert keyboard is not None
    assert keyboard.inline_keyboard[0][0].text == "Подключить Google Календарь"
    assert keyboard.inline_keyboard[0][0].url.startswith(f"{onboarding.PUBLIC_SITE_URL}/connect#token=")
