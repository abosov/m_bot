import types

import pytest
from aiogram.filters import CommandObject

from handlers.personal_bot.routers.common import start as start_router


class DummyMessage:
    def __init__(self, from_user=None):
        self.answers = []
        self.from_user = from_user
        self.text = ""
        self.bot = types.SimpleNamespace(id=1)

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class DummyCallback:
    def __init__(self, message):
        self.message = message
        self.bot = types.SimpleNamespace(id=1)
        self.from_user = message.from_user
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


@pytest.mark.asyncio
async def test_personal_start_specialist_with_incomplete_onboarding_shows_defaults(monkeypatch):
    from_user = types.SimpleNamespace(id=987, full_name="Dr Gregory House", first_name="Gregory", last_name="House")
    message = DummyMessage(from_user=from_user)

    specialist = types.SimpleNamespace(onboarding_master_completed_at=None, onboarding_personal_completed_at=None)
    profile = types.SimpleNamespace(
        session_duration_min=60,
        session_buffer_min=10,
        specialist_timezone="UTC",
        max_sessions_per_day=4,
        slot_step_min=15,
        cancel_window_hours=12,
    )

    async def fake_load(_specialist_id):
        return specialist, profile

    async def fake_ensure(_specialist_id):
        return None

    monkeypatch.setattr(start_router, "_load_specialist_and_profile", fake_load)
    monkeypatch.setattr(start_router, "_ensure_defaults_exist", fake_ensure)

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="specialist",
        specialist_id="sp-id",
        public_name=None,
        owner_tg_user_id=None,
    )

    assert any("Настройки по умолчанию" in msg[0] for msg in message.answers)
    assert any("Текущий календарь: не выбран" in msg[0] for msg in message.answers)
    assert not any("Доступно сейчас" in msg[0] for msg in message.answers)


@pytest.mark.asyncio
async def test_personal_start_specialist_completed_onboarding_opens_owner_panel(monkeypatch):
    captured = {}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        captured["specialist_id"] = specialist_id
        captured["public_name"] = public_name
        captured["owner_tg_user_id"] = owner_tg_user_id

    specialist = types.SimpleNamespace(onboarding_master_completed_at="2026-02-12T00:00:00Z", onboarding_personal_completed_at="2026-02-12T00:00:00Z")
    profile = types.SimpleNamespace()

    async def fake_load(_specialist_id):
        return specialist, profile

    monkeypatch.setattr(start_router, "_load_specialist_and_profile", fake_load)
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
async def test_onboarding_keep_sets_full_onboarding_and_opens_owner_panel(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=111))
    callback = DummyCallback(message)
    calls = {"committed": False, "owner_panel": False}

    specialist = types.SimpleNamespace(onboarding_master_completed_at=None, onboarding_personal_completed_at=None)

    class _Session:
        async def get(self, model, specialist_id):
            return specialist

        async def commit(self):
            calls["committed"] = True

    class _Ctx:
        async def __aenter__(self):
            return _Session()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_send_owner_panel(*args, **kwargs):
        calls["owner_panel"] = True

    monkeypatch.setattr(start_router, "async_session_factory", lambda: _Ctx())
    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)

    await start_router.onboarding_keep(
        callback=callback,
        specialist_id="sp-id",
        public_name="Doc",
        owner_tg_user_id=111,
    )

    assert specialist.onboarding_personal_completed_at is not None
    assert calls["committed"] is True
    assert calls["owner_panel"] is True


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
async def test_personal_start_specialist_owner_panel_exception_sends_fallback(monkeypatch):
    async def fake_send_owner_panel(*args, **kwargs):
        raise RuntimeError("boom")

    specialist = types.SimpleNamespace(
        onboarding_master_completed_at="2026-02-12T00:00:00Z",
        onboarding_personal_completed_at="2026-02-12T00:00:00Z",
    )

    async def fake_load(_specialist_id):
        return specialist, types.SimpleNamespace()

    monkeypatch.setattr(start_router, "_load_specialist_and_profile", fake_load)
    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)

    from_user = types.SimpleNamespace(id=987, full_name="Dr Gregory House", first_name="Gregory", last_name="House")
    message = DummyMessage(from_user=from_user)

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="specialist",
        specialist_id="sp-id",
        public_name=None,
        owner_tg_user_id=None,
    )

    assert any("Возникла ошибка при открытии панели" in msg[0] for msg in message.answers)
    assert not any("Доступно сейчас" in msg[0] for msg in message.answers)


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

def test_onboarding_keyboard_with_calendar_contains_calendar_and_existing_actions():
    keyboard = start_router._onboarding_keyboard_with_calendar()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert "calendar:switch_stub" in callback_data
    assert "onboarding:keep" in callback_data
    assert "onboarding:change" in callback_data
