import types
from datetime import datetime, timezone

import pytest

from database import BookingState
from handlers.personal_bot.routers.client import commands as client_commands


class DummyMessage:
    def __init__(self, from_user):
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return list(self._values)


class _SessionStub:
    def __init__(self, client, appointments):
        self._client = client
        self._appointments = appointments
        self._execute_calls = 0

    async def execute(self, _stmt):
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _ScalarResult(self._client)
        if self._execute_calls == 2:
            return _ScalarsResult(self._appointments)
        raise AssertionError("Unexpected execute() call")


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def _mock_google_create(monkeypatch):
    async def _fake_create_appointment_event(**_kwargs):
        return {"id": "fake-event-id"}

    monkeypatch.setattr(client_commands, "create_appointment_event", _fake_create_appointment_event)


def _extract_inline_buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


@pytest.mark.asyncio
async def test_my_appointments_shows_empty_text_and_refresh_button(monkeypatch):
    client = types.SimpleNamespace(client_id="cl-1", client_timezone="UTC")
    session = _SessionStub(client=client, appointments=[])
    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _SessionContext(session))

    message = DummyMessage(from_user=types.SimpleNamespace(id=1001))

    await client_commands.client_my_appointments_button(message, actor="client", specialist_id="sp-id")

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert "У вас нет будущих записей." in text

    markup = kwargs["reply_markup"]
    buttons = _extract_inline_buttons(markup)
    assert any(button.text == "Обновить" and button.callback_data == "client_appt:list" for button in buttons)


@pytest.mark.asyncio
async def test_my_appointments_shows_confirmed_and_failed_with_retry_button(monkeypatch):
    client = types.SimpleNamespace(client_id="cl-1", client_timezone="UTC")
    appointments = [
        types.SimpleNamespace(
            start_at_utc=datetime(2099, 1, 10, 9, 30, tzinfo=timezone.utc),
            booking_state=BookingState.confirmed,
        ),
        types.SimpleNamespace(
            start_at_utc=datetime(2099, 1, 11, 15, 45, tzinfo=timezone.utc),
            booking_state=BookingState.failed,
        ),
    ]
    session = _SessionStub(client=client, appointments=appointments)
    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _SessionContext(session))

    message = DummyMessage(from_user=types.SimpleNamespace(id=1002))

    await client_commands.client_my_appointments_button(message, actor="client", specialist_id="sp-id")

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert "Ваши записи:" in text
    assert "2099-01-10 09:30" in text
    assert "2099-01-11 15:45" in text
    assert "не подтверждена" in text

    markup = kwargs["reply_markup"]
    buttons = _extract_inline_buttons(markup)
    assert any(
        button.text == "Повторить последнюю не подтвержденную"
        and button.callback_data == "client_appt:retry_last"
        for button in buttons
    )
