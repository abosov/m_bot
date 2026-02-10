import uuid

import pytest
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

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
    monkeypatch.setattr(
        personal_dispatcher,
        "build_bot_from_db",
        lambda tg_bot: Bot(token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"),
    )

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

    assert captured["actor"] == "specialist"
    assert captured["specialist_id"] == specialist_id
    assert captured["owner_tg_user_id"] == 777
