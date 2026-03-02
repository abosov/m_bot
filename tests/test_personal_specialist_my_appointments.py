import types
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from database import BookingState
from handlers.personal_bot.routers.specialist import commands as specialist_commands


class DummyMessage:
    def __init__(self, from_user):
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_specialist_my_appointments_shows_statuses_and_quick_actions(monkeypatch):
    awaiting_id = uuid4()
    appointments = [
        (
            types.SimpleNamespace(
                appointment_id=awaiting_id,
                start_at_utc=datetime(2099, 2, 1, 9, 0, tzinfo=timezone.utc),
                booking_state=BookingState.awaiting_specialist_confirmation,
            ),
            types.SimpleNamespace(display_name="Анна", tg_username="anna"),
        ),
        (
            types.SimpleNamespace(
                appointment_id=uuid4(),
                start_at_utc=datetime(2099, 2, 1, 12, 0, tzinfo=timezone.utc),
                booking_state=BookingState.rejected_by_specialist,
            ),
            types.SimpleNamespace(display_name="", tg_username="client_2"),
        ),
    ]

    async def _fake_load(_specialist_id):
        return types.SimpleNamespace(specialist_timezone="UTC"), appointments

    monkeypatch.setattr(specialist_commands, "_load_specialist_appointments", _fake_load)

    message = DummyMessage(from_user=types.SimpleNamespace(id=5001))

    await specialist_commands.specialist_my_appointments(
        message,
        specialist_id="sp-id",
        actor="specialist",
    )

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert "Мои записи:" in text
    assert "Ожидает вашего подтверждения" in text
    assert "Отклонено" in text

    markup = kwargs["reply_markup"]
    buttons = [button for row in markup.inline_keyboard for button in row]
    assert [button.text for button in buttons] == ["✅ Подтвердить", "❌ Отклонить"]
    assert [button.callback_data for button in buttons] == [
        f"sp_appt_decision:confirm:{awaiting_id}",
        f"sp_appt_decision:reject:{awaiting_id}",
    ]


@pytest.mark.asyncio
async def test_specialist_my_appointments_returns_for_non_specialist(monkeypatch):
    called = False

    async def _fake_load(_specialist_id):
        nonlocal called
        called = True
        return None, []

    monkeypatch.setattr(specialist_commands, "_load_specialist_appointments", _fake_load)
    message = DummyMessage(from_user=types.SimpleNamespace(id=5002))

    await specialist_commands.specialist_my_appointments(message, specialist_id="sp-id", actor="client")

    assert called is False
    assert message.answers == []


@pytest.mark.asyncio
async def test_specialist_analytics_blocks_start_and_shows_pricing_button(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=5003))

    async def _load_plan(_specialist_id):
        return specialist_commands.TariffPlan.start

    monkeypatch.setattr(specialist_commands, "_load_specialist_tariff_plan", _load_plan)

    await specialist_commands.specialist_analytics(message, specialist_id="sp-id", actor="specialist")

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert text == "📊 Аналитика доступна на тарифе Pro. Обновите тариф для доступа к статистике."
    markup = kwargs["reply_markup"]
    button = markup.inline_keyboard[0][0]
    assert button.text == "Перейти к тарифам"


@pytest.mark.asyncio
async def test_specialist_analytics_allows_team(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=5004))

    async def _load_plan(_specialist_id):
        return specialist_commands.TariffPlan.team

    monkeypatch.setattr(specialist_commands, "_load_specialist_tariff_plan", _load_plan)

    await specialist_commands.specialist_analytics(message, specialist_id="sp-id", actor="specialist")

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert text == "📊 Раздел аналитики доступен на вашем тарифе. Скоро здесь появится статистика."
    assert kwargs == {}
