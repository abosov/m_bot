import types
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from handlers.personal_bot.routers.client import commands as client_commands


class DummyMessage:
    def __init__(self, text: str, from_user=None):
        self.text = text
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class DummyState:
    def __init__(self):
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


@pytest.mark.asyncio
async def test_client_menu_buttons_return_stubs():
    book_msg = DummyMessage("Записаться")
    state = DummyState()

    async def _tz(_specialist_id):
        return ZoneInfo("UTC")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(client_commands, "_get_specialist_tz", _tz)
    monkeypatch.setattr(
        client_commands,
        "_first_available_day",
        lambda **_kwargs: date(2026, 2, 20),
    )

    await client_commands.client_book_button(book_msg, actor="client", state=state, specialist_id="sp-id")
    monkeypatch.undo()

    assert book_msg.answers[0][0] == "Выберите день:"
    assert book_msg.answers[0][1].get("reply_markup") is not None
    assert state.state == client_commands.ClientBookingState.waiting_for_day
    assert state.data["booking_available_days"] == [
        "2026-02-20",
        "2026-02-21",
        "2026-02-22",
        "2026-02-23",
        "2026-02-24",
        "2026-02-25",
        "2026-02-26",
    ]

    appts_msg = DummyMessage("Мои записи (пока stub)")
    await client_commands.client_my_appointments_button(appts_msg, actor="client")
    assert "скоро будет доступен" in appts_msg.answers[0][0]

    tz_msg = DummyMessage("Сменить часовой пояс (пока stub)")
    await client_commands.client_change_timezone_button(tz_msg, actor="client")
    assert "скоро будет доступна" in tz_msg.answers[0][0]


def test_first_available_day_cutoff_rules():
    tz = ZoneInfo("Europe/Moscow")

    before_cutoff = datetime(2026, 2, 15, 17, 0, tzinfo=timezone.utc)
    assert client_commands._first_available_day(now_utc=before_cutoff, specialist_tz=tz) == date(2026, 2, 16)

    after_cutoff = datetime(2026, 2, 15, 19, 0, tzinfo=timezone.utc)
    assert client_commands._first_available_day(now_utc=after_cutoff, specialist_tz=tz) == date(2026, 2, 17)


@pytest.mark.asyncio
async def test_client_pick_day_updates_fsm_and_replies():
    state = DummyState()
    message = DummyMessage("")

    callback = types.SimpleNamespace(
        data="client_book_day:2026-02-21",
        message=message,
        answers=[],
    )

    async def _callback_answer():
        callback.answers.append(True)

    callback.answer = _callback_answer

    await client_commands.client_pick_day(callback, state=state)

    assert state.data["booking_date"] == "2026-02-21"
    assert message.answers[0][0] == "Вы выбрали 21.02.2026. Далее будет выбор времени (в разработке)."
    assert callback.answers == [True]


@pytest.mark.asyncio
async def test_client_capture_display_name_saves_name_and_shows_menu(monkeypatch):
    message = DummyMessage("Анна", from_user=types.SimpleNamespace(id=42))
    client = types.SimpleNamespace(display_name=None)

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return client

    class _Session:
        def __init__(self):
            self.committed = False

        async def execute(self, _stmt):
            return _Result()

        async def commit(self):
            self.committed = True

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(client_commands, "async_session_factory", lambda: _Ctx())

    await client_commands.client_capture_display_name(message, actor="client", specialist_id="sp-id")

    assert client.display_name == "Анна"
    assert session.committed is True
    assert "Приятно познакомиться" in message.answers[0][0]
    assert message.answers[0][1].get("reply_markup") is not None
