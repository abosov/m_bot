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

    specialist = types.SimpleNamespace(onboarding_master_completed_at=None, onboarding_personal_completed_at=None, profile=None)
    profile = types.SimpleNamespace(
        session_duration_min=60,
        session_buffer_min=10,
        specialist_timezone="UTC",
        max_sessions_per_day=4,
        slot_step_min=15,
        cancel_window_hours=12,
        onboarding_completed=False,
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

    assert any("Google Calendar:" in msg[0] for msg in message.answers)
    assert any("• Календарь: не выбран" in msg[0] for msg in message.answers)
    assert any("• Часовой пояс специалиста (для расчётов): UTC (совпадает с Google Calendar)" in msg[0] for msg in message.answers)
    assert not any("Доступно сейчас" in msg[0] for msg in message.answers)


@pytest.mark.asyncio
async def test_personal_start_specialist_completed_onboarding_opens_owner_panel(monkeypatch):
    captured = {}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        captured["specialist_id"] = specialist_id
        captured["public_name"] = public_name
        captured["owner_tg_user_id"] = owner_tg_user_id

    profile = types.SimpleNamespace(specialist_timezone="UTC", session_duration_min=60, cancel_window_hours=12, onboarding_completed=True)
    specialist = types.SimpleNamespace(
        onboarding_master_completed_at="2026-02-12T00:00:00Z",
        onboarding_personal_completed_at="2026-02-12T00:00:00Z",
        google_oauth=types.SimpleNamespace(status="connected"),
        calendar_settings=types.SimpleNamespace(calendar_id="cal"),
        calendar_sync_states=[object()],
        profile=profile,
    )

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
    quick_menu_messages = [msg for msg in message.answers if "Доступно сейчас" in msg[0]]
    assert quick_menu_messages
    markup = quick_menu_messages[-1][1]["reply_markup"]
    callback_data = [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]
    help_queries = [button.switch_inline_query_current_chat for row in markup.inline_keyboard for button in row if button.switch_inline_query_current_chat]
    assert callback_data == ["open_settings", "calendar:switch_stub", "calendar:smoke"]
    assert help_queries == ["/help"]


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

    profile = types.SimpleNamespace(specialist_timezone="UTC", session_duration_min=60, cancel_window_hours=12, onboarding_completed=True)
    specialist = types.SimpleNamespace(
        onboarding_master_completed_at="2026-02-12T00:00:00Z",
        onboarding_personal_completed_at="2026-02-12T00:00:00Z",
        google_oauth=types.SimpleNamespace(status="connected"),
        calendar_settings=types.SimpleNamespace(calendar_id="cal"),
        calendar_sync_states=[object()],
        profile=profile,
    )

    async def fake_load(_specialist_id):
        return specialist, profile

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
async def test_personal_start_client_creates_client_and_requests_display_name(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=1, username="client1", full_name="Client", first_name="Client", last_name=None))

    class _Result:
        @staticmethod
        def scalar_one_or_none():
            return None

    class _Session:
        def __init__(self):
            self.added = []

        async def execute(self, _stmt):
            return _Result()

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            return None

        async def refresh(self, _obj):
            return None

    session = _Session()

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(start_router, "async_session_factory", lambda: _Ctx())

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="client",
        specialist_id="sp-id",
        public_name=None,
        owner_tg_user_id=None,
    )

    assert len(message.answers) == 1
    assert "Как к вам обращаться" in message.answers[0][0]
    assert len(session.added) == 1
    assert session.added[0].tg_user_id == 1

def test_onboarding_keyboard_with_calendar_contains_calendar_and_existing_actions():
    keyboard = start_router._onboarding_keyboard_with_calendar()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == [
        "calendar:switch_stub",
        "onboarding:change",
        "onboarding:keep",
        "onboarding:later",
    ]


def test_specialist_quick_menu_keyboard_contains_required_actions():
    keyboard = start_router._specialist_quick_menu_keyboard(has_selected_calendar=False)
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]
    help_queries = [button.switch_inline_query_current_chat for row in keyboard.inline_keyboard for button in row if button.switch_inline_query_current_chat]
    texts = [button.text for row in keyboard.inline_keyboard for button in row]

    assert callback_data == ["open_settings", "calendar:switch_stub", "calendar:smoke"]
    assert help_queries == ["/help"]
    assert "📅 Календарь" in texts

    keyboard_with_calendar = start_router._specialist_quick_menu_keyboard(has_selected_calendar=True)
    texts_with_calendar = [button.text for row in keyboard_with_calendar.inline_keyboard for button in row]
    assert "📅 Сменить календарь" in texts_with_calendar


@pytest.mark.asyncio
async def test_render_onboarding_screen_has_expected_headings_and_no_ambiguous_timezone_label(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=123, full_name="Dr House", first_name="Gregory", last_name="House"))

    specialist = types.SimpleNamespace(
        calendar_settings=types.SimpleNamespace(
            calendar_id="cal-1",
            calendar_summary="Основной календарь",
            calendar_time_zone="Europe/Moscow",
            last_smoke_test_status="ok",
        )
    )
    profile = types.SimpleNamespace(
        session_duration_min=60,
        session_buffer_min=10,
        slot_step_min=15,
        max_sessions_per_day=4,
        cancel_window_hours=12,
        specialist_timezone="Europe/Moscow",
    )

    async def fake_ensure(_specialist_id):
        return None

    async def fake_load(_specialist_id):
        return specialist, profile

    monkeypatch.setattr(start_router, "_ensure_defaults_exist", fake_ensure)
    monkeypatch.setattr(start_router, "_load_specialist_and_profile", fake_load)

    await start_router._render_onboarding_screen(message=message, specialist_id="sp-id")

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert "Google Calendar:" in text
    assert "Параметры записи:" in text
    assert "Часовой пояс:" not in text
    assert "Часовой пояс календаря (Google):" in text
    assert "Часовой пояс специалиста (для расчётов):" in text

    callback_data = [button.callback_data for row in kwargs["reply_markup"].inline_keyboard for button in row]
    assert callback_data == [
        "calendar:switch_stub",
        "onboarding:change",
        "onboarding:keep",
        "onboarding:later",
    ]


@pytest.mark.asyncio
async def test_personal_start_specialist_with_incomplete_basic_setup_shows_settings_button(monkeypatch):
    from_user = types.SimpleNamespace(id=987, full_name="Dr Gregory House", first_name="Gregory", last_name="House")
    message = DummyMessage(from_user=from_user)

    profile = types.SimpleNamespace(
        specialist_timezone="",
        session_duration_min=60,
        cancel_window_hours=12,
        onboarding_completed=False,
    )
    specialist = types.SimpleNamespace(
        onboarding_master_completed_at="2026-02-12T00:00:00Z",
        onboarding_personal_completed_at="2026-02-12T00:00:00Z",
        google_oauth=None,
        calendar_settings=None,
        calendar_sync_states=[],
        profile=profile,
    )

    async def fake_load(_specialist_id):
        return specialist, profile

    called = {"owner_panel": False}

    async def fake_send_owner_panel(*args, **kwargs):
        called["owner_panel"] = True

    monkeypatch.setattr(start_router, "_load_specialist_and_profile", fake_load)
    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)

    await start_router.personal_start(
        message=message,
        command=CommandObject(prefix="/", command="start", mention=None, args=None),
        actor="specialist",
        specialist_id="sp-id",
        public_name=None,
        owner_tg_user_id=None,
    )

    assert called["owner_panel"] is False
    assert any("Личный бот готов к работе" in msg[0] for msg in message.answers)
    assert any("Рекомендуем завершить первоначальную настройку" in msg[0] for msg in message.answers)
    markup = message.answers[-1][1]["reply_markup"]
    callback_data = [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]
    help_queries = [button.switch_inline_query_current_chat for row in markup.inline_keyboard for button in row if button.switch_inline_query_current_chat]
    button_texts = [button.text for row in markup.inline_keyboard for button in row]
    assert callback_data == ["open_settings", "calendar:switch_stub", "calendar:smoke"]
    assert help_queries == ["/help"]
    assert "📅 Календарь" in button_texts


@pytest.mark.asyncio
async def test_open_settings_callback_opens_owner_panel(monkeypatch):
    message = DummyMessage(from_user=types.SimpleNamespace(id=111))
    callback = DummyCallback(message)
    called = {}

    async def fake_send_owner_panel(message, specialist_id, public_name, owner_tg_user_id=None):
        called["specialist_id"] = specialist_id
        called["public_name"] = public_name
        called["owner_tg_user_id"] = owner_tg_user_id

    monkeypatch.setattr(start_router, "send_owner_panel", fake_send_owner_panel)

    await start_router.open_settings(
        callback=callback,
        specialist_id="sp-id",
        public_name="Doc",
        owner_tg_user_id=111,
    )

    assert callback.answered is True
    assert called == {"specialist_id": "sp-id", "public_name": "Doc", "owner_tg_user_id": 111}
