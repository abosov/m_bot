import logging
import uuid

import pytest
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

from handlers.personal_bot import router as personal_router
from handlers.personal_bot.routers.client import commands as client_commands
from handlers.personal_bot.role_guard import SpecialistRoleGuardMiddleware
from services.telegram import personal_dispatcher


class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@pytest.mark.asyncio
async def test_personal_context_middleware_detects_specialist_actor(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
            return Result(profile)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    middleware = personal_dispatcher.PersonalContextMiddleware()
    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    update = Update.model_validate(
        {
            "update_id": 1,
            "message": {
                "message_id": 10,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    seen = {}

    async def handler(event, data):
        seen.update({k: data.get(k) for k in ["actor", "specialist_id", "owner_tg_user_id", "public_name"]})
        return None

    await middleware(handler, update, {"telegram_bot": tg_bot})

    assert seen == {
        "actor": "specialist",
        "specialist_id": specialist_id,
        "owner_tg_user_id": 777,
        "public_name": "Dr. House",
    }


@pytest.mark.asyncio
async def test_personal_context_middleware_detects_client_actor(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
            return Result(profile)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    middleware = personal_dispatcher.PersonalContextMiddleware()
    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    update = Update.model_validate(
        {
            "update_id": 2,
            "message": {
                "message_id": 11,
                "date": 1,
                "chat": {"id": 888, "type": "private"},
                "from": {"id": 888, "is_bot": False, "first_name": "Client"},
                "text": "/start",
            },
        }
    )

    seen = {}

    async def handler(event, data):
        seen.update({k: data.get(k) for k in ["actor", "owner_tg_user_id"]})
        return None

    await middleware(handler, update, {"telegram_bot": tg_bot})

    assert seen == {"actor": "client", "owner_tg_user_id": 777}


@pytest.mark.asyncio
async def test_process_update_routes_owner_to_specialist_handler(monkeypatch):
    personal_dispatcher._profile_cache.clear()
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
            return Result(profile)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    captured = {}
    router = Router()

    @router.message(CommandStart())
    async def start_handler(message: Message, actor: str, specialist_id, owner_tg_user_id):
        captured["actor"] = actor
        captured["specialist_id"] = specialist_id
        captured["owner_tg_user_id"] = owner_tg_user_id

    dp = Dispatcher()
    dp.update.middleware(personal_dispatcher.PersonalContextMiddleware())
    dp.include_router(router)

    monkeypatch.setattr(personal_dispatcher, "get_personal_dispatcher", lambda: dp)
    test_bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

    async def fake_get_personal_bot(tg_bot):
        return test_bot

    monkeypatch.setattr(personal_dispatcher, "get_personal_bot", fake_get_personal_bot)

    tg_bot = type("TgBot", (), {"specialist_id": specialist_id, "bot_user_id": 123})()
    raw_update = {
        "update_id": 3,
        "message": {
            "message_id": 1,
            "date": 1,
            "chat": {"id": 777, "type": "private"},
            "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
            "text": "/start",
        },
    }

    await personal_dispatcher.process_update(tg_bot, raw_update)
    await test_bot.session.close()

    assert captured["actor"] == "specialist"
    assert captured["specialist_id"] == specialist_id
    assert captured["owner_tg_user_id"] == 777


@pytest.mark.asyncio
async def test_specialist_role_guard_blocks_client(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
            return Result(profile)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    denied_messages = []

    async def fake_answer(self, text, *args, **kwargs):
        denied_messages.append(text)
        return None

    monkeypatch.setattr(Message, "answer", fake_answer)

    specialist_router = Router()
    specialist_router.message.middleware(SpecialistRoleGuardMiddleware())
    reached = {"value": False}

    @specialist_router.message(CommandStart())
    async def specialist_only_handler(message: Message):
        reached["value"] = True

    dp = Dispatcher()
    dp.update.middleware(personal_dispatcher.PersonalContextMiddleware())
    dp.include_router(specialist_router)

    update = Update.model_validate(
        {
            "update_id": 4,
            "message": {
                "message_id": 10,
                "date": 1,
                "chat": {"id": 888, "type": "private"},
                "from": {"id": 888, "is_bot": False, "first_name": "Client"},
                "text": "/start",
            },
        }
    )

    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    try:
        await dp.feed_update(bot, update, telegram_bot=tg_bot)
    finally:
        await bot.session.close()

    assert reached["value"] is False
    assert denied_messages == ["ℹ️ Команда доступна только специалисту."]


@pytest.mark.asyncio
async def test_specialist_role_guard_allows_specialist(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
            return Result(profile)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    specialist_router = Router()
    specialist_router.message.middleware(SpecialistRoleGuardMiddleware())
    reached = {"value": False}

    @specialist_router.message(CommandStart())
    async def specialist_only_handler(message: Message):
        reached["value"] = True

    dp = Dispatcher()
    dp.update.middleware(personal_dispatcher.PersonalContextMiddleware())
    dp.include_router(specialist_router)

    update = Update.model_validate(
        {
            "update_id": 5,
            "message": {
                "message_id": 10,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    try:
        await dp.feed_update(bot, update, telegram_bot=tg_bot)
    finally:
        await bot.session.close()

    assert reached["value"] is True


@pytest.mark.asyncio
async def test_personal_context_middleware_uses_auth_tg_user_id_when_profile_owner_missing(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            model_name = stmt.column_descriptions[0]["entity"].__name__
            if model_name == "SpecialistProfile":
                profile = type("Profile", (), {"owner_tg_user_id": None, "public_name": "Dr. House"})()
                return Result(profile)
            auth = type("Auth", (), {"tg_user_id": 777})()
            return Result(auth)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    middleware = personal_dispatcher.PersonalContextMiddleware()
    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    update = Update.model_validate(
        {
            "update_id": 6,
            "message": {
                "message_id": 12,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    seen = {}

    async def handler(event, data):
        seen.update({k: data.get(k) for k in ["actor", "owner_tg_user_id", "public_name"]})
        return None

    await middleware(handler, update, {"telegram_bot": tg_bot})

    assert seen == {"actor": "specialist", "owner_tg_user_id": 777, "public_name": "Dr. House"}


@pytest.mark.asyncio
async def test_personal_global_error_middleware_replies_in_private_chat(monkeypatch):
    replies = []

    async def fake_answer(self, text, *args, **kwargs):
        replies.append(text)
        return None

    monkeypatch.setattr(Message, "answer", fake_answer)

    middleware = personal_dispatcher.PersonalGlobalErrorMiddleware()
    update = Update.model_validate(
        {
            "update_id": 7,
            "message": {
                "message_id": 13,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    async def broken_handler(event, data):
        raise RuntimeError("boom")

    tg_bot = type("TgBot", (), {"bot_username": "x_bot", "bot_user_id": 123})()
    await middleware(broken_handler, update, {"telegram_bot": tg_bot})

    assert any("Произошла ошибка при обработке команды" in text for text in replies)


@pytest.mark.asyncio
async def test_client_can_view_own_appointments_after_confirmation_feature(monkeypatch):
    specialist_id = uuid.uuid4()

    class Session:
        async def execute(self, stmt):
            model_name = stmt.column_descriptions[0]["entity"].__name__
            if model_name == "SpecialistProfile":
                profile = type("Profile", (), {"owner_tg_user_id": 777, "public_name": "Dr. House"})()
                return Result(profile)
            auth = type("Auth", (), {"tg_user_id": 777})()
            return Result(auth)

    monkeypatch.setattr(personal_dispatcher, "async_session_factory", lambda: DummySessionCtx(Session()))

    sent_messages = []

    async def fake_answer(self, text, *args, **kwargs):
        sent_messages.append(text)
        return None

    async def fake_render(message, specialist_id, tg_user_id):
        await message.answer("Ваши записи (UTC):\n2099-02-01 Пн [09:00] — Подтверждена")

    monkeypatch.setattr(Message, "answer", fake_answer)
    monkeypatch.setattr(client_commands, "_render_client_appointments", fake_render)

    dp = Dispatcher()
    dp.update.middleware(personal_dispatcher.PersonalContextMiddleware())
    dp.include_router(personal_router)

    update = Update.model_validate(
        {
            "update_id": 8,
            "message": {
                "message_id": 20,
                "date": 1,
                "chat": {"id": 888, "type": "private"},
                "from": {"id": 888, "is_bot": False, "first_name": "Client"},
                "text": "Мои записи",
            },
        }
    )

    tg_bot = type("TgBot", (), {"specialist_id": specialist_id})()
    bot = Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    try:
        await dp.feed_update(bot, update, telegram_bot=tg_bot)
    finally:
        await bot.session.close()

    assert sent_messages == ["Ваши записи (UTC):\n2099-02-01 Пн [09:00] — Подтверждена"]


@pytest.mark.asyncio
async def test_personal_global_error_middleware_logs_context(monkeypatch, caplog):
    async def fake_answer(self, text, *args, **kwargs):
        return None

    monkeypatch.setattr(Message, "answer", fake_answer)

    middleware = personal_dispatcher.PersonalGlobalErrorMiddleware()
    update = Update.model_validate(
        {
            "update_id": 77,
            "message": {
                "message_id": 13,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    async def broken_handler(event, data):
        raise RuntimeError("boom")

    specialist_id = uuid.uuid4()
    tg_bot = type(
        "TgBot",
        (),
        {"bot_username": "x_bot", "bot_user_id": 123, "specialist_id": specialist_id},
    )()

    with caplog.at_level(logging.ERROR):
        await middleware(broken_handler, update, {"telegram_bot": tg_bot})

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "personal bot unhandled exception" in logs
    assert str(specialist_id) in logs
    assert "update_id=77" in logs


@pytest.mark.asyncio
async def test_personal_global_error_middleware_state_mismatch_no_notify_and_shows_menu(monkeypatch):
    replies = []
    notify_calls = []

    async def fake_answer(self, text, *args, **kwargs):
        replies.append((text, kwargs))
        return None

    async def fake_notify(*args, **kwargs):
        notify_calls.append((args, kwargs))

    monkeypatch.setattr(Message, "answer", fake_answer)
    monkeypatch.setattr(personal_dispatcher, "notify_exception", fake_notify)

    middleware = personal_dispatcher.PersonalGlobalErrorMiddleware()
    update = Update.model_validate(
        {
            "update_id": 88,
            "message": {
                "message_id": 13,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "Записаться",
            },
        }
    )

    async def broken_handler(event, data):
        raise personal_dispatcher.StateMismatchError("state mismatch")

    await middleware(broken_handler, update, {"actor": "client", "telegram_bot": object()})

    assert notify_calls == []
    assert any("Похоже, Вы начали не с /start" in text for text, _ in replies)
    assert any(text == "Меню клиента:" for text, _ in replies)


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [RuntimeError("boom"), KeyError("x")])
async def test_personal_global_error_middleware_runtime_notifies_and_support_message(monkeypatch, exc):
    replies = []
    notify_calls = []

    async def fake_answer(self, text, *args, **kwargs):
        replies.append(text)
        return None

    async def fake_notify(*args, **kwargs):
        notify_calls.append((args, kwargs))

    monkeypatch.setattr(Message, "answer", fake_answer)
    monkeypatch.setattr(personal_dispatcher, "notify_exception", fake_notify)

    middleware = personal_dispatcher.PersonalGlobalErrorMiddleware()
    update = Update.model_validate(
        {
            "update_id": 89,
            "message": {
                "message_id": 13,
                "date": 1,
                "chat": {"id": 777, "type": "private"},
                "from": {"id": 777, "is_bot": False, "first_name": "Owner"},
                "text": "/start",
            },
        }
    )

    async def broken_handler(event, data):
        raise exc

    await middleware(broken_handler, update, {"actor": "client", "telegram_bot": object()})

    assert len(notify_calls) == 1
    assert any("Произошла ошибка при обработке команды" in text for text in replies)
