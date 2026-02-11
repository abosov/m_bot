import pytest
from aiogram.filters import CommandObject

from handlers.personal_bot.routers.common import start as start_router


class DummyMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_personal_start_owner_panel_payload_routes_to_owner_flow(monkeypatch):
    called = {"value": False}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        called["value"] = True
        assert specialist_id == "sp-id"
        assert public_name == "Dr. House"

    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)
    message = DummyMessage()

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args="owner_panel"),
        actor="specialist",
        specialist_id="sp-id",
        public_name="Dr. House",
        owner_tg_user_id=123,
    )

    assert called["value"] is True
    assert len(message.answers) == 1
    assert "Доступно сейчас" in message.answers[0][0]


@pytest.mark.asyncio
async def test_personal_start_without_payload_shows_owner_panel(monkeypatch):
    called = {"value": False}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        called["value"] = True
        assert specialist_id == "sp-id"
        assert public_name == "Dr. House"

    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)
    message = DummyMessage()

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="specialist",
        specialist_id="sp-id",
        public_name="Dr. House",
        owner_tg_user_id=123,
    )

    assert called["value"] is True
    assert len(message.answers) == 1
    assert "Доступно сейчас" in message.answers[0][0]
