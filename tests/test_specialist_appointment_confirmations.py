from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from database import Appointment, BookingState
from handlers.personal_bot.routers.specialist import appointment_confirmations


class DummyMessage:
    def __init__(self):
        self.answers = []
        self.edits = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_reply_markup(self, **kwargs):
        self.edits.append(kwargs)


@pytest.mark.asyncio
async def test_specialist_confirm_callback_updates_request(monkeypatch):
    appointment_id = uuid4()
    callback_answers = []
    message = DummyMessage()

    callback = SimpleNamespace(
        data=f"sp_appt_decision:confirm:{appointment_id}",
        message=message,
    )

    async def _callback_answer(*args, **kwargs):
        callback_answers.append((args, kwargs))

    callback.answer = _callback_answer

    class DummySessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_confirm(_session, *, appointment_id, specialist_id):
        assert specialist_id == "sp-1"
        assert appointment_id
        return SimpleNamespace(status="updated")

    monkeypatch.setattr(appointment_confirmations, "async_session_factory", lambda: DummySessionCtx())
    monkeypatch.setattr(appointment_confirmations, "confirm_appointment_by_specialist", fake_confirm)

    await appointment_confirmations.specialist_appointment_decision(callback, specialist_id="sp-1")

    assert message.edits == [{"reply_markup": None}]
    assert callback_answers[0][0] == ("✅ Запись подтверждена",)


@pytest.mark.asyncio
async def test_specialist_reject_callback_shows_stale_for_processed(monkeypatch):
    appointment_id = uuid4()
    callback_answers = []
    message = DummyMessage()

    callback = SimpleNamespace(
        data=f"sp_appt_decision:reject:{appointment_id}",
        message=message,
    )

    async def _callback_answer(*args, **kwargs):
        callback_answers.append((args, kwargs))

    callback.answer = _callback_answer

    class Session:
        async def execute(self, _query):
            return SimpleNamespace(
                scalar_one_or_none=lambda: Appointment(
                    appointment_id=appointment_id,
                    specialist_id=uuid4(),
                    client_id=uuid4(),
                    start_at_utc=datetime.now(timezone.utc),
                    end_at_utc=datetime.now(timezone.utc),
                    booking_state=BookingState.confirmed,
                    idempotency_key="k",
                )
            )

    class DummySessionCtx:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(appointment_confirmations, "async_session_factory", lambda: DummySessionCtx())

    await appointment_confirmations.specialist_appointment_decision(callback, specialist_id=uuid4())

    assert callback_answers[0][0] == ("Эта заявка уже обработана или устарела.",)
    assert callback_answers[0][1]["show_alert"] is True


@pytest.mark.asyncio
async def test_specialist_reject_callback_opens_reason_screen(monkeypatch):
    specialist_id = uuid4()
    appointment_id = uuid4()
    callback_answers = []
    message = DummyMessage()

    callback = SimpleNamespace(
        data=f"sp_appt_decision:reject:{appointment_id}",
        message=message,
    )

    async def _callback_answer(*args, **kwargs):
        callback_answers.append((args, kwargs))

    callback.answer = _callback_answer

    class Session:
        async def execute(self, _query):
            return SimpleNamespace(
                scalar_one_or_none=lambda: Appointment(
                    appointment_id=appointment_id,
                    specialist_id=specialist_id,
                    client_id=uuid4(),
                    start_at_utc=datetime.now(timezone.utc),
                    end_at_utc=datetime.now(timezone.utc),
                    booking_state=BookingState.awaiting_specialist_confirmation,
                    idempotency_key="k",
                )
            )

    class DummySessionCtx:
        async def __aenter__(self):
            return Session()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(appointment_confirmations, "async_session_factory", lambda: DummySessionCtx())

    await appointment_confirmations.specialist_appointment_decision(callback, specialist_id=specialist_id)

    assert message.answers[0][0] == "Выберите причину отклонения:"
    keyboard = message.answers[0][1]["reply_markup"]
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert len(buttons) == 3
    assert buttons[0].callback_data == f"sp_appt_reject_reason:{appointment_id}:time"
    assert callback_answers[0][0] == ()
