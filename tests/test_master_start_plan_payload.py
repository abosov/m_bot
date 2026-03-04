import types

import pytest
from aiogram.filters import CommandObject

import handlers.master_onboarding as onboarding


class DummyState:
    def __init__(self):
        self.cleared = False

    async def clear(self):
        self.cleared = True


class DummyMessage:
    def __init__(self):
        self.from_user = types.SimpleNamespace(id=77, username="tester", first_name="T", last_name="E")
        self.bot = object()


@pytest.mark.asyncio
async def test_cmd_start_plan_payload_shows_plan_card_without_db(monkeypatch):
    message = DummyMessage()
    state = DummyState()
    captured = {}

    async def _fake_send(_message, text, **kwargs):
        captured["text"] = text
        captured["reply_markup"] = kwargs.get("reply_markup")

    async def _fake_log(*args, **kwargs):
        return None

    def _fail_session_factory():
        raise AssertionError("DB should not be used for plan_* payload")

    monkeypatch.setattr(onboarding, "_send_safe_html_message", _fake_send)
    monkeypatch.setattr(onboarding, "log_outbound_message", _fake_log)
    monkeypatch.setattr(onboarding, "async_session_factory", _fail_session_factory)

    await onboarding.cmd_start(
        message,
        state,
        command=CommandObject(prefix="/", command="start", mention=None, args="plan_pro_y"),
    )

    assert state.cleared is True
    assert "Вы выбрали тариф <b>Pro</b> (год)" in captured["text"]
    buttons = captured["reply_markup"].inline_keyboard
    assert buttons[0][0].text == "Продолжить → Оплатить"
    assert buttons[0][0].callback_data == "plan:pay_stub:pro:y"


def test_parse_plan_payload_team_contact_supported():
    assert onboarding._parse_plan_start_payload("plan_team_contact") == (onboarding.TariffPlan.team, "m")
    assert onboarding._parse_plan_start_payload("plan_start_m") == (onboarding.TariffPlan.start, "m")
    assert onboarding._parse_plan_start_payload("plan_unknown_m") is None
