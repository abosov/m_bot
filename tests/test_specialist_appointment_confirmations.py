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


class DummyState:
    def __init__(self):
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.state = None
        self.data = {}


def _appointment(*, appointment_id, specialist_id, booking_state):
    return Appointment(
        appointment_id=appointment_id,
        specialist_id=specialist_id,
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=booking_state,
        idempotency_key="k",
    )


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
async def test_specialist_reject_callback_opens_reason_mode_screen(monkeypatch):
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

    async def fake_resolve(_appointment_id, _specialist_id):
        return _appointment(
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            booking_state=BookingState.awaiting_specialist_confirmation,
        )

    monkeypatch.setattr(appointment_confirmations, "_resolve_pending_appointment", fake_resolve)

    await appointment_confirmations.specialist_appointment_decision(callback, specialist_id=specialist_id)

    assert message.answers[0][0] == "Добавить пояснение клиенту?"
    keyboard = message.answers[0][1]["reply_markup"]
    buttons = [button for row in keyboard.inline_keyboard for button in row]
    assert buttons[0].callback_data == f"sp_appt_reject_mode:with_reason:{appointment_id}"
    assert buttons[1].callback_data == f"sp_appt_reject_mode:no_reason:{appointment_id}"
    assert callback_answers[0][0] == ()


@pytest.mark.asyncio
async def test_specialist_reject_without_reason_completes(monkeypatch):
    specialist_id = uuid4()
    appointment_id = uuid4()
    callback_answers = []
    message = DummyMessage()
    state = DummyState()

    callback = SimpleNamespace(
        data=f"sp_appt_reject_mode:no_reason:{appointment_id}",
        message=message,
    )

    async def _callback_answer(*args, **kwargs):
        callback_answers.append((args, kwargs))

    callback.answer = _callback_answer

    async def fake_resolve(_appointment_id, _specialist_id):
        return _appointment(
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            booking_state=BookingState.awaiting_specialist_confirmation,
        )

    class DummySessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_reject(_session, **kwargs):
        assert kwargs["rejection_reason"] is None
        return SimpleNamespace(status="updated")

    monkeypatch.setattr(appointment_confirmations, "_resolve_pending_appointment", fake_resolve)
    monkeypatch.setattr(appointment_confirmations, "async_session_factory", lambda: DummySessionCtx())
    monkeypatch.setattr(appointment_confirmations, "reject_appointment_by_specialist", fake_reject)

    await appointment_confirmations.specialist_appointment_reject_mode(callback, specialist_id=specialist_id, state=state)

    assert message.edits == [{"reply_markup": None}]
    assert message.answers[0][0] == "Отклонено"
    assert state.state is None
    assert callback_answers[0][0] == ()


@pytest.mark.asyncio
async def test_specialist_reject_reason_validation_empty_text(monkeypatch):
    specialist_id = uuid4()
    appointment_id = uuid4()
    message = SimpleNamespace(text="   ", answers=[])
    state = DummyState()
    state.data["appointment_id"] = str(appointment_id)

    async def answer(text, **kwargs):
        message.answers.append((text, kwargs))

    message.answer = answer

    await appointment_confirmations.specialist_appointment_reject_reason_input(
        message,
        specialist_id=specialist_id,
        state=state,
    )

    assert "Пояснение не должно быть пустым" in message.answers[0][0]
    keyboard = message.answers[0][1]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == f"sp_appt_reject_mode:no_reason:{appointment_id}"


@pytest.mark.asyncio
async def test_specialist_reject_reason_validation_too_long(monkeypatch):
    specialist_id = uuid4()
    appointment_id = uuid4()
    too_long = "x" * (appointment_confirmations._REJECTION_REASON_LIMIT + 1)
    message = SimpleNamespace(text=too_long, answers=[])
    state = DummyState()
    state.data["appointment_id"] = str(appointment_id)

    async def answer(text, **kwargs):
        message.answers.append((text, kwargs))

    message.answer = answer

    await appointment_confirmations.specialist_appointment_reject_reason_input(
        message,
        specialist_id=specialist_id,
        state=state,
    )

    assert "слишком длинное" in message.answers[0][0]


@pytest.mark.asyncio
async def test_specialist_reject_with_reason_completes_and_clears_state(monkeypatch):
    specialist_id = uuid4()
    appointment_id = uuid4()
    message = SimpleNamespace(text="Нужно перенести", answers=[])
    state = DummyState()
    state.state = appointment_confirmations.SpecialistAppointmentRejectStates.waiting_rejection_reason
    state.data["appointment_id"] = str(appointment_id)

    async def answer(text, **kwargs):
        message.answers.append((text, kwargs))

    message.answer = answer

    async def fake_resolve(_appointment_id, _specialist_id):
        return _appointment(
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            booking_state=BookingState.awaiting_specialist_confirmation,
        )

    class DummySessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_reject(_session, **kwargs):
        assert kwargs["rejection_reason"] == "Нужно перенести"
        return SimpleNamespace(status="updated")

    monkeypatch.setattr(appointment_confirmations, "_resolve_pending_appointment", fake_resolve)
    monkeypatch.setattr(appointment_confirmations, "async_session_factory", lambda: DummySessionCtx())
    monkeypatch.setattr(appointment_confirmations, "reject_appointment_by_specialist", fake_reject)

    await appointment_confirmations.specialist_appointment_reject_reason_input(
        message,
        specialist_id=specialist_id,
        state=state,
    )

    assert message.answers[0][0] == "Отклонено"
    assert state.state is None
    assert state.data == {}
