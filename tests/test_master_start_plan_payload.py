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


class DummyCallbackMessage:
    def __init__(self):
        self.bot = object()
        self.calls = []

    async def answer(self, text, **kwargs):
        self.calls.append((text, kwargs))


class DummyCallback:
    def __init__(self, data: str):
        self.data = data
        self.from_user = types.SimpleNamespace(id=77, username="tester", first_name="T", last_name="E")
        self.message = DummyCallbackMessage()
        self.answered = []

    async def answer(self, text=None, show_alert=False):
        self.answered.append((text, show_alert))




class DummyCallbackState:
    def __init__(self):
        self._state = "existing"

    async def clear(self):
        self._state = None

    async def get_state(self):
        return self._state

    async def set_state(self, value):
        self._state = value

class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_cmd_start_plan_payload_shows_plan_card_and_ensures_profile(monkeypatch):
    message = DummyMessage()
    state = DummyState()
    captured = {}
    ensured = {"called": False}

    async def _fake_send(_message, text, **kwargs):
        captured["text"] = text
        captured["reply_markup"] = kwargs.get("reply_markup")

    async def _fake_log(*args, **kwargs):
        return None

    async def _fake_ensure(**kwargs):
        ensured["called"] = True

    monkeypatch.setattr(onboarding, "_send_safe_html_message", _fake_send)
    monkeypatch.setattr(onboarding, "log_outbound_message", _fake_log)
    monkeypatch.setattr(onboarding, "async_session_factory", lambda: _FakeSession())
    monkeypatch.setattr(onboarding, "ensure_specialist_with_profile_for_tg_user", _fake_ensure)

    await onboarding.cmd_start(
        message,
        state,
        command=CommandObject(prefix="/", command="start", mention=None, args="plan_pro_y"),
    )

    assert ensured["called"] is True
    assert state.cleared is True
    assert "Вы выбрали тариф <b>Pro</b> (год)" in captured["text"]
    buttons = captured["reply_markup"].inline_keyboard
    assert buttons[0][0].text == "Перейти к оплате"
    assert buttons[0][0].callback_data == "plan:pay_stub:pro:y"
    assert buttons[1][0].callback_data == "onboarding:start"


@pytest.mark.asyncio
async def test_plan_pay_stub_sends_payment_button(monkeypatch):
    callback = DummyCallback("plan:pay_stub:start:m")

    async def _fake_ensure(**kwargs):
        return types.SimpleNamespace(specialist_id="sp-1")

    async def _fake_create_purchase(specialist_id, tg_user_id, plan, period):
        assert specialist_id == "sp-1"
        assert tg_user_id == 77
        assert str(plan.value) == "start"
        assert period == "m"
        return "token", "https://zumbot.ru/pay?token=abc"

    async def _fake_send(message, text, **kwargs):
        await message.answer(text, **kwargs)

    monkeypatch.setattr(onboarding, "async_session_factory", lambda: _FakeSession())
    monkeypatch.setattr(onboarding, "ensure_specialist_with_profile_for_tg_user", _fake_ensure)
    monkeypatch.setattr(onboarding, "create_subscription_purchase", _fake_create_purchase)
    monkeypatch.setattr(onboarding, "_send_safe_html_message", _fake_send)

    await onboarding.plan_pay_stub(callback)

    assert callback.message.calls
    text, kwargs = callback.message.calls[-1]
    assert "Ссылка на оплату" in text
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert keyboard[0][0].text == "Открыть страницу оплаты"
    assert keyboard[1][0].callback_data == "onboarding:start"


def test_parse_plan_payload_team_contact_supported():
    assert onboarding._parse_plan_start_payload("plan_team_contact") == (onboarding.TariffPlan.team, "m")
    assert onboarding._parse_plan_start_payload("plan_start_m") == (onboarding.TariffPlan.start, "m")
    assert onboarding._parse_plan_start_payload("plan_unknown_m") is None


@pytest.mark.asyncio
async def test_plan_check_payment_shows_continue_onboarding_when_not_completed(monkeypatch):
    callback = DummyCallback("plan:check_payment")

    async def _fake_status(_tg_user_id):
        return "Статус подписки:\n• План: start"

    async def _fake_completed(_tg_user_id):
        return False

    monkeypatch.setattr(onboarding, "get_latest_purchase_status_text", _fake_status)
    monkeypatch.setattr(onboarding, "_is_master_onboarding_completed", _fake_completed)

    await onboarding.plan_check_payment(callback)

    text, kwargs = callback.message.calls[-1]
    assert "Статус подписки" in text
    keyboard = kwargs["reply_markup"].inline_keyboard
    assert keyboard[0][0].callback_data == "onboarding:start"


@pytest.mark.asyncio
async def test_onboarding_start_callback_for_completed_user_routes_to_main(monkeypatch):
    callback = DummyCallback("onboarding:start")
    state = DummyCallbackState()
    called = {"cmd_start": False}

    async def _fake_completed(_tg_user_id):
        return True

    async def _fake_cmd_start(message, fsm_state, command=None):
        called["cmd_start"] = True

    monkeypatch.setattr(onboarding, "_is_master_onboarding_completed", _fake_completed)
    monkeypatch.setattr(onboarding, "cmd_start", _fake_cmd_start)

    await onboarding.onboarding_start_from_plan(callback, state)

    assert called["cmd_start"] is True
