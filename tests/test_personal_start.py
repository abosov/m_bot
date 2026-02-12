import types

import pytest
from aiogram.filters import CommandObject

from handlers.personal_bot.routers.common import start as start_router


class DummyMessage:
    def __init__(self, from_user=None):
        self.answers = []
        self.from_user = from_user

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_personal_start_specialist_fallbacks_from_message_user(monkeypatch):
    captured = {}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        captured["specialist_id"] = specialist_id
        captured["public_name"] = public_name
        captured["owner_tg_user_id"] = owner_tg_user_id

    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)
    from_user = types.SimpleNamespace(
        id=987,
        full_name="Dr Gregory House",
        first_name="Gregory",
        last_name="House",
    )
    message = DummyMessage(from_user=from_user)

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="specialist",
        specialist_id="sp-id",
        public_name=None,
        owner_tg_user_id=None,
    )

    assert captured["specialist_id"] == "sp-id"
    assert captured["public_name"] == "Dr Gregory House"
    assert captured["owner_tg_user_id"] == 987
    assert any("Доступно сейчас" in msg[0] for msg in message.answers)


@pytest.mark.asyncio
async def test_personal_start_specialist_without_specialist_id_sends_error(monkeypatch):
    called = {"value": False}

    async def fake_send_owner_panel(*args, **kwargs):
        called["value"] = True

    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)
    from_user = types.SimpleNamespace(id=555, full_name="Spec User", first_name="Spec", last_name="User")
    message = DummyMessage(from_user=from_user)

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args="owner_panel"),
        actor="specialist",
        specialist_id=None,
        public_name=None,
        owner_tg_user_id=None,
    )

    assert called["value"] is False
    assert len(message.answers) == 1
    assert "Не удалось определить профиль специалиста" in message.answers[0][0]


@pytest.mark.asyncio
async def test_personal_start_client_gets_placeholder():
    message = DummyMessage(from_user=types.SimpleNamespace(id=1, full_name="Client", first_name="Client", last_name=None))

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="client",
        specialist_id=None,
        public_name=None,
        owner_tg_user_id=None,
    )

    assert len(message.answers) == 1
    assert "клиентская заглушка" in message.answers[0][0]
