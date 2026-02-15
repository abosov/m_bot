import types

import pytest

from handlers.personal_bot.routers.client import commands as client_commands


class DummyMessage:
    def __init__(self, text: str, from_user=None):
        self.text = text
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_client_menu_buttons_return_stubs():
    book_msg = DummyMessage("Записаться")
    await client_commands.client_book_button(book_msg, actor="client")
    assert book_msg.answers[0][0] == "Запись скоро будет доступна."

    appts_msg = DummyMessage("Мои записи (пока stub)")
    await client_commands.client_my_appointments_button(appts_msg, actor="client")
    assert "скоро будет доступен" in appts_msg.answers[0][0]

    tz_msg = DummyMessage("Сменить часовой пояс (пока stub)")
    await client_commands.client_change_timezone_button(tz_msg, actor="client")
    assert "скоро будет доступна" in tz_msg.answers[0][0]


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
