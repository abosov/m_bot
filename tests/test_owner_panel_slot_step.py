from datetime import time

import pytest

from handlers.personal_bot.routers.specialist import owner_panel


def test_slot_step_allowed_values() -> None:
    keyboard = owner_panel._slot_step_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks == [
        "owner:slot_step:60",
        "owner:slot_step:30",
        "owner:slot_step:15",
        "owner:slot_step:10",
        "owner:slot_step:5",
    ]


def test_slot_step_default_is_15() -> None:
    assert owner_panel._DEFAULT_SLOT_STEP_MIN == 15


def test_max_sessions_keyboard_has_values_up_to_20() -> None:
    keyboard = owner_panel._max_sessions_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks[0] == "owner:max_sessions:1"
    assert callbacks[-1] == "owner:max_sessions:20"
    assert len(callbacks) == 20


def test_owner_panel_defaults_constants() -> None:
    assert owner_panel._DEFAULT_WORKING_HOURS == [
        (time(9, 0), time(12, 0)),
        (time(13, 0), time(17, 0)),
        (time(17, 0), time(21, 0)),
    ]
    assert owner_panel._DEFAULT_DURATION_MIN == 60
    assert owner_panel._DEFAULT_BUFFER_MIN == 10
    assert owner_panel._DEFAULT_CANCEL_WINDOW_HOURS == 12
    assert owner_panel._DEFAULT_MAX_SESSIONS_PER_DAY == 4
    assert owner_panel._DEFAULT_SLOT_STEP_MIN == 15


def test_validate_interval_pair_allows_both_null() -> None:
    owner_panel._validate_interval_pair(start=None, end=None)


def test_validate_interval_pair_rejects_half_filled_pair() -> None:
    with pytest.raises(owner_panel.AvailabilityValidationError):
        owner_panel._validate_interval_pair(start=time(9, 0), end=None)
    with pytest.raises(owner_panel.AvailabilityValidationError):
        owner_panel._validate_interval_pair(start=None, end=time(12, 0))


def test_validate_interval_pair_rejects_non_positive_interval() -> None:
    with pytest.raises(owner_panel.AvailabilityValidationError):
        owner_panel._validate_interval_pair(start=time(12, 0), end=time(12, 0))


class DummyMessage:
    def __init__(self):
        self.answers = []
        self.edits = []
        self.chat = type("Chat", (), {"id": 1})()
        self.message_id = 1

        class _Bot:
            def __init__(self, outer):
                self.outer = outer

            async def edit_message_text(self, *, chat_id, message_id, text, reply_markup=None):
                self.outer.edits.append((text, {"chat_id": chat_id, "message_id": message_id, "reply_markup": reply_markup}))

        self.bot = _Bot(self)

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


class DummyCallback:
    def __init__(self):
        self.message = DummyMessage()
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_apply_defaults_requests_confirmation() -> None:
    callback = DummyCallback()

    await owner_panel.owner_panel_apply_defaults(callback=callback)

    assert callback.message.edits[0][0] == "Вы уверены, что хотите сбросить настройки?"
    keyboard = callback.message.edits[0][1]["reply_markup"]
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks == ["owner_panel:apply_defaults:confirm", "owner_panel:apply_defaults:cancel"]


@pytest.mark.asyncio
async def test_apply_defaults_confirm_calls_reset_service_and_returns_to_owner_panel(monkeypatch) -> None:
    captured = {"reset": 0, "owner_panel": 0}

    async def fake_reset(_specialist_id):
        captured["reset"] += 1
        assert _specialist_id == "sp-id"
        return {
            "session_duration_min": 60,
            "session_buffer_min": 10,
            "slot_step_min": 15,
            "max_sessions_per_day": 4,
            "schedule": {weekday: [] for weekday in range(7)},
        }

    async def fake_render_owner_panel_inplace(message, specialist_id, public_name, owner_tg_user_id=None):
        captured["owner_panel"] += 1
        assert specialist_id == "sp-id"

    monkeypatch.setattr(owner_panel, "reset_specialist_settings_to_default", fake_reset)
    monkeypatch.setattr(owner_panel, "_render_owner_panel_inplace", fake_render_owner_panel_inplace)

    callback = DummyCallback()

    await owner_panel.owner_panel_apply_defaults_confirm(
        callback=callback,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. House",
    )

    assert captured == {"reset": 1, "owner_panel": 1}


@pytest.mark.asyncio
async def test_apply_defaults_cancel_sends_cancel_message(monkeypatch) -> None:
    callback = DummyCallback()
    captured = {"owner_panel": 0}

    async def fake_render_owner_panel_inplace(*args, **kwargs):
        captured["owner_panel"] += 1

    monkeypatch.setattr(owner_panel, "_render_owner_panel_inplace", fake_render_owner_panel_inplace)

    await owner_panel.owner_panel_apply_defaults_cancel(
        callback=callback,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert callback.answers[0][0] == "Отменено"
    assert captured["owner_panel"] == 1




@pytest.mark.asyncio
async def test_owner_panel_profile_edit_link_generates_fresh_url_each_tap(monkeypatch) -> None:
    callback = DummyCallback()
    callback.from_user = type("User", (), {"id": 123})()

    calls = {"n": 0}

    class _SessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_build_profile_edit_url_for_specialist(*, session, specialist_id, tg_user_id):
        assert specialist_id == "sp-id"
        assert tg_user_id == 123
        calls["n"] += 1
        return f"https://example.test/profile/edit#token=fresh-{calls['n']}"

    monkeypatch.setattr(owner_panel, "async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(owner_panel, "build_profile_edit_url_for_specialist", fake_build_profile_edit_url_for_specialist)

    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)
    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)

    assert calls["n"] == 2
    assert callback.message.answers[0][0].startswith("Откройте редактор профиля по свежей ссылке")
    first_button = callback.message.answers[0][1]["reply_markup"].inline_keyboard[0][0]
    second_button = callback.message.answers[1][1]["reply_markup"].inline_keyboard[0][0]
    assert first_button.url.endswith("fresh-1")
    assert second_button.url.endswith("fresh-2")




@pytest.mark.asyncio
async def test_owner_panel_callback_provides_new_link_after_old_message_link_expired(monkeypatch) -> None:
    callback = DummyCallback()
    callback.from_user = type("User", (), {"id": 123})()

    generated_urls: list[str] = []

    class _SessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_build_profile_edit_url_for_specialist(*, session, specialist_id, tg_user_id):
        token_idx = len(generated_urls) + 1
        fresh_url = f"https://example.test/profile/edit#token=fresh-{token_idx}"
        generated_urls.append(fresh_url)
        return fresh_url

    monkeypatch.setattr(owner_panel, "async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(owner_panel, "build_profile_edit_url_for_specialist", fake_build_profile_edit_url_for_specialist)

    # old link from an earlier bot message is conceptually expired/used at this point;
    # user taps callback again and must receive a fresh link
    old_message_link = "https://example.test/profile/edit#token=expired-old"
    assert old_message_link.endswith("expired-old")

    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)

    assert generated_urls == ["https://example.test/profile/edit#token=fresh-1"]
    url_button = callback.message.answers[-1][1]["reply_markup"].inline_keyboard[0][0]
    assert url_button.url == "https://example.test/profile/edit#token=fresh-1"

@pytest.mark.asyncio
async def test_owner_panel_profile_edit_link_denies_non_owner() -> None:
    callback = DummyCallback()
    callback.from_user = type("User", (), {"id": 999})()

    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)

    assert callback.answers[-1][0] == "Недостаточно прав"
    assert callback.answers[-1][1].get("show_alert") is True
    assert callback.message.answers == []


@pytest.mark.asyncio
async def test_owner_panel_profile_edit_link_allows_new_link_after_error(monkeypatch) -> None:
    callback = DummyCallback()
    callback.from_user = type("User", (), {"id": 123})()

    calls = {"n": 0}

    class _SessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_build_profile_edit_url_for_specialist(*, session, specialist_id, tg_user_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("PUBLIC_SITE_URL is missing")
        return "https://example.test/profile/edit#token=fresh-2"

    monkeypatch.setattr(owner_panel, "async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(owner_panel, "build_profile_edit_url_for_specialist", fake_build_profile_edit_url_for_specialist)

    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)
    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)

    assert callback.answers[0][0] == "Ссылка временно недоступна"
    assert callback.answers[0][1].get("show_alert") is True
    assert callback.message.answers[-1][1]["reply_markup"].inline_keyboard[0][0].url.endswith("fresh-2")


@pytest.mark.asyncio
async def test_owner_panel_profile_edit_link_sends_plain_text_without_raw_url_or_parse_mode(monkeypatch) -> None:
    callback = DummyCallback()
    callback.from_user = type("User", (), {"id": 123})()

    class _SessionCtx:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fresh_url = "https://example.test/profile/edit#token=fresh_1-abc=xyz"

    async def fake_build_profile_edit_url_for_specialist(*, session, specialist_id, tg_user_id):
        assert specialist_id == "sp-id"
        assert tg_user_id == 123
        return fresh_url

    monkeypatch.setattr(owner_panel, "async_session_factory", lambda: _SessionCtx())
    monkeypatch.setattr(owner_panel, "build_profile_edit_url_for_specialist", fake_build_profile_edit_url_for_specialist)

    await owner_panel.owner_panel_profile_edit_link(callback=callback, specialist_id="sp-id", owner_tg_user_id=123)

    text, kwargs = callback.message.answers[-1]
    assert text == (
        "Откройте редактор профиля по свежей ссылке.\n"
        "Ссылка одноразовая и действует ограниченное время."
    )
    assert fresh_url not in text
    assert "parse_mode" in kwargs
    assert kwargs["parse_mode"] is None

    keyboard = kwargs["reply_markup"]
    url_button = keyboard.inline_keyboard[0][0]
    assert url_button.url == fresh_url

def test_format_intervals_for_ui_hides_null_intervals() -> None:
    row = type(
        "Row",
        (),
        {
            "interval_1_start": time(9, 0),
            "interval_1_end": time(12, 0),
            "interval_2_start": None,
            "interval_2_end": None,
            "interval_3_start": time(17, 0),
            "interval_3_end": time(21, 0),
        },
    )()

    assert owner_panel._format_intervals_for_ui(row) == "09:00–12:00, 17:00–21:00"


def test_owner_panel_keyboard_has_calendar_menu_button() -> None:
    profile = type("Profile", (), {"specialist_timezone": "UTC", "session_duration_min": 60, "session_buffer_min": 10, "slot_step_min": 15, "max_sessions_per_day": 4, "cancel_window_hours": 12})()
    text, keyboard = owner_panel.build_specialist_settings_view(
        profile=profile,
        rows=[],
        calendar_settings=None,
        keep_button_text="✅ Оставить как есть",
        keep_callback_data="onboarding:keep",
        include_reset_button=True,
    )
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "owner_panel:calendar_menu" in callbacks
    assert "Календарь:" in text


@pytest.mark.asyncio
async def test_owner_cal_create_returns_soft_refusal_and_calendar_menu() -> None:
    callback = DummyCallback()

    await owner_panel.owner_calendar_create(
        callback=callback,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert not callback.message.answers
    assert len(callback.message.edits) == 1
    text = callback.message.edits[0][0]
    assert "Сейчас Zumbot подключается только к уже существующему календарю Google." in text
    assert "Выберите действие с календарём:" in text
    keyboard = callback.message.edits[0][1]["reply_markup"]
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks == ["owner_cal:select", "owner_cal:smoke", "owner_cal:back"]


def test_validate_session_settings_input_accepts_valid_values() -> None:
    owner_panel._validate_session_settings_input(duration=60, buffer=10)


def test_validate_session_settings_input_rejects_invalid_values() -> None:
    with pytest.raises(owner_panel.SpecialistScheduleValidationError):
        owner_panel._validate_session_settings_input(duration=10, buffer=10)
    with pytest.raises(owner_panel.SpecialistScheduleValidationError):
        owner_panel._validate_session_settings_input(duration=62, buffer=10)
    with pytest.raises(owner_panel.SpecialistScheduleValidationError):
        owner_panel._validate_session_settings_input(duration=60, buffer=121)


class DummyState:
    def __init__(self):
        self.current_state = None
        self.data = {}

    async def set_state(self, state):
        self.current_state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.current_state = None
        self.data = {}


@pytest.mark.asyncio
async def test_limits_fsm_flow_saves_and_confirms(monkeypatch) -> None:
    state = DummyState()
    callback = DummyCallback()
    first_message = DummyMessage()
    second_message = DummyMessage()

    profile = type("Profile", (), {"session_duration_min": 60, "max_sessions_per_day": 4, "slot_step_min": 15})()

    async def fake_load_profile_and_rows(_specialist_id):
        return profile, []

    async def fake_update_limits(_specialist_id, max_per_day, slot_step):
        assert max_per_day == 12
        assert slot_step == 15
        return {"max_sessions_per_day": max_per_day, "slot_step_min": slot_step}

    called = {"owner_panel": 0}

    async def fake_send_owner_panel(*args, **kwargs):
        called["owner_panel"] += 1

    monkeypatch.setattr(owner_panel, "_load_profile_and_rows", fake_load_profile_and_rows)
    monkeypatch.setattr(owner_panel, "update_limits", fake_update_limits)
    monkeypatch.setattr(owner_panel, "send_owner_panel", fake_send_owner_panel)

    await owner_panel.owner_panel_slot_params_menu(callback=callback, state=state, specialist_id="sp-id")
    assert state.current_state == owner_panel.LimitsSettingsStates.waiting_for_daily_limit
    assert "✅ Лимиты сохранены" in callback.message.edits[-1][0]

    first_message.text = "12"
    await owner_panel.owner_panel_receive_max_sessions(first_message, state=state, specialist_id="sp-id")
    assert state.current_state == owner_panel.LimitsSettingsStates.waiting_for_slot_step
    assert first_message.answers[-1][0] == "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
    assert first_message.edits == []

    second_message.text = "15"
    await owner_panel.owner_panel_receive_slot_step(
        second_message,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state is None
    assert "✅ Лимиты сохранены" in second_message.answers[-1][0]
    assert called == {"owner_panel": 1}


@pytest.mark.asyncio
async def test_limits_fsm_rejects_invalid_slot_step(monkeypatch) -> None:
    state = DummyState()
    message = DummyMessage()
    state.data = {"limits_max_sessions_candidate": 8}

    called = {"update": 0}

    async def fake_update_limits(*args, **kwargs):
        called["update"] += 1
        return {}

    monkeypatch.setattr(owner_panel, "update_limits", fake_update_limits)

    message.text = "55"
    await owner_panel.owner_panel_receive_slot_step(
        message,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    last_text = message.edits[-1][0] if message.edits else message.answers[-1][0]
    assert "не больше 50" in last_text
    assert called == {"update": 0}


def test_timezone_keyboard_has_popular_and_manual_actions() -> None:
    keyboard = owner_panel._timezone_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "owner_tz:set:UTC" in callbacks
    assert "owner_tz:set:Europe/Berlin" in callbacks
    assert "owner_tz:manual" in callbacks
    assert "owner_tz:back" in callbacks


@pytest.mark.asyncio
async def test_timezone_fsm_flow_manual_input_saves_and_confirms(monkeypatch) -> None:
    state = DummyState()
    callback = DummyCallback()
    message = DummyMessage()

    captured = {"owner_panel": 0}

    async def fake_update_specialist_timezone(_specialist_id, timezone_name):
        assert _specialist_id == "sp-id"
        assert timezone_name == "Europe/Berlin"
        return {"specialist_timezone": timezone_name}

    async def fake_send_owner_panel(*args, **kwargs):
        captured["owner_panel"] += 1

    monkeypatch.setattr(owner_panel, "update_specialist_timezone", fake_update_specialist_timezone)
    monkeypatch.setattr(owner_panel, "send_owner_panel", fake_send_owner_panel)

    await owner_panel.owner_panel_change_timezone(callback=callback, state=state)
    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_for_timezone
    last_timezone_prompt = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Выберите часовой пояс" in last_timezone_prompt
    assert "Страница: 1/3" in last_timezone_prompt

    keyboard = callback.message.edits[-1][1]["reply_markup"]
    callbacks = {button.callback_data for row in keyboard.inline_keyboard for button in row}
    assert "owner_tz:manual" in callbacks
    assert "owner_tz:page:2" in callbacks

    message.text = "Europe/Berlin"
    await owner_panel.owner_panel_timezone_manual_input(
        message=message,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state is None
    assert "✅ Часовой пояс специалиста сохранён" in message.answers[-1][0]
    assert captured == {"owner_panel": 1}


@pytest.mark.asyncio
async def test_timezone_manual_callback_switches_state_and_prompts_input() -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:manual"

    await owner_panel.owner_panel_timezone_manual(callback=callback, state=state)

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_manual_timezone
    last_text = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Введите timezone вручную" in last_text
    assert "Europe/Berlin" in last_text


@pytest.mark.asyncio
async def test_timezone_page_callback_renders_requested_page_and_keeps_state() -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:page:2"

    await owner_panel.owner_panel_timezone_page(callback=callback, state=state)

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_for_timezone
    last_text = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Страница: 2/3" in last_text

    keyboard = callback.message.edits[-1][1]["reply_markup"]
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "owner_tz:page:3" in callbacks


@pytest.mark.asyncio
async def test_timezone_page_callback_clamps_invalid_page_to_bounds() -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:page:999"

    await owner_panel.owner_panel_timezone_page(callback=callback, state=state)

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_for_timezone
    last_text = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Страница: 3/3" in last_text


@pytest.mark.asyncio
async def test_timezone_set_callback_saves_and_returns_to_owner_panel(monkeypatch) -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:set:Europe/Berlin"

    async def fake_update_specialist_timezone(_specialist_id, timezone_name):
        assert _specialist_id == "sp-id"
        assert timezone_name == "Europe/Berlin"
        return {"specialist_timezone": timezone_name}

    captured = {"owner_panel": 0}

    async def fake_render_owner_panel_inplace(*args, **kwargs):
        captured["owner_panel"] += 1

    monkeypatch.setattr(owner_panel, "update_specialist_timezone", fake_update_specialist_timezone)
    monkeypatch.setattr(owner_panel, "_render_owner_panel_inplace", fake_render_owner_panel_inplace)

    await owner_panel.owner_panel_timezone_set(
        callback=callback,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state is None
    assert callback.answers[-1][0] == "✅ Часовой пояс специалиста сохранён"
    assert captured == {"owner_panel": 1}


@pytest.mark.asyncio
async def test_timezone_set_callback_invalid_iana_keeps_state_and_picker() -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:set:Mars/Olympus"
    state.data = {"owner_panel_tz_page": 2}

    await owner_panel.owner_panel_timezone_set(
        callback=callback,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_for_timezone
    last_text = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Не удалось сохранить timezone" in last_text
    assert "Страница: 2/3" in last_text


@pytest.mark.asyncio
async def test_timezone_set_callback_save_error_keeps_state_and_picker(monkeypatch) -> None:
    state = DummyState()
    callback = DummyCallback()
    callback.data = "owner_tz:set:Europe/Berlin"

    async def fake_update_specialist_timezone(_specialist_id, timezone_name):
        raise owner_panel.SpecialistScheduleValidationError(f"timezone does not exist: {timezone_name}")

    monkeypatch.setattr(owner_panel, "update_specialist_timezone", fake_update_specialist_timezone)

    await owner_panel.owner_panel_timezone_set(
        callback=callback,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_for_timezone
    last_text = callback.message.edits[-1][0] if callback.message.edits else callback.message.answers[-1][0]
    assert "Не удалось сохранить timezone" in last_text
    assert "Страница: 1/3" in last_text


@pytest.mark.asyncio
async def test_timezone_fsm_keeps_state_on_validation_error(monkeypatch) -> None:
    state = DummyState()
    message = DummyMessage()

    async def fake_update_specialist_timezone(_specialist_id, timezone_name):
        raise owner_panel.SpecialistScheduleValidationError(f"timezone does not exist: {timezone_name}")

    monkeypatch.setattr(owner_panel, "update_specialist_timezone", fake_update_specialist_timezone)

    message.text = "Mars/Olympus"
    await owner_panel.owner_panel_timezone_manual_input(
        message=message,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert state.current_state == owner_panel.TimezoneSettingsStates.waiting_manual_timezone
    assert "Не удалось сохранить timezone" in message.answers[-1][0]


@pytest.mark.asyncio
async def test_build_owner_panel_view_has_reset_and_stable_primary_button_order(monkeypatch) -> None:
    profile = type(
        "Profile",
        (),
        {
            "public_name": "Dr. House",
            "specialist_timezone": "UTC",
            "session_duration_min": 60,
            "session_buffer_min": 10,
            "slot_step_min": 15,
            "max_sessions_per_day": 4,
            "cancel_window_hours": 12,
        },
    )()

    async def fake_load_profile_and_rows(_specialist_id):
        return profile, []

    async def fake_load_calendar_settings(_specialist_id):
        return None

    class _Repo:
        async def get_working_intervals(self, _specialist_id):
            return {}

    async def fake_load_public_page_url_for_settings(_specialist_id):
        return None

    monkeypatch.setattr(owner_panel, "_load_profile_and_rows", fake_load_profile_and_rows)
    monkeypatch.setattr(owner_panel, "_load_calendar_settings", fake_load_calendar_settings)
    monkeypatch.setattr(owner_panel, "_load_public_page_url_for_settings", fake_load_public_page_url_for_settings)
    monkeypatch.setattr(owner_panel, "WorkingIntervalsRepository", _Repo)

    panel_view = await owner_panel._build_owner_panel_view(specialist_id="sp-id", public_name=None, owner_tg_user_id=123)

    assert panel_view is not None
    _text, keyboard = panel_view
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]
    assert "owner_panel:apply_defaults" in callbacks
    assert callbacks[:5] == [
        "owner_panel:calendar_menu",
        "owner_panel:change_duration_buffer",
        "owner_panel:slot_params_menu",
        "owner_panel:change_timezone",
        "owner_panel:change_schedule",
    ]


@pytest.mark.asyncio
async def test_send_owner_panel_always_sends_single_unified_main_screen_message(monkeypatch) -> None:
    message = DummyMessage()

    async def fake_ensure_defaults(*, specialist_id, owner_tg_user_id, public_name):
        return True

    async def fake_build_view(*, specialist_id, public_name, owner_tg_user_id):
        keyboard = owner_panel.InlineKeyboardMarkup(
            inline_keyboard=[[owner_panel.InlineKeyboardButton(text="reset", callback_data="owner_panel:apply_defaults")]]
        )
        return "✅ Базовые настройки уже применены автоматически после онбординга, Dr. Test.\nХотите изменить их сейчас?", keyboard

    monkeypatch.setattr(owner_panel, "_ensure_owner_panel_defaults", fake_ensure_defaults)
    monkeypatch.setattr(owner_panel, "_build_owner_panel_view", fake_build_view)

    await owner_panel.send_owner_panel(
        message=message,
        specialist_id="sp-id",
        public_name="Dr. Test",
        owner_tg_user_id=123,
    )

    assert len(message.answers) == 1
    text, kwargs = message.answers[0]
    assert "Базовые настройки уже применены автоматически после онбординга" in text
    callback_data = [button.callback_data for row in kwargs["reply_markup"].inline_keyboard for button in row if button.callback_data]
    assert callback_data == ["owner_panel:apply_defaults"]


@pytest.mark.asyncio
async def test_first_open_and_back_render_identical_main_screen_callbacks(monkeypatch) -> None:
    first_open_message = DummyMessage()
    back_message = DummyMessage()

    async def fake_ensure_defaults(*, specialist_id, owner_tg_user_id, public_name):
        return False

    async def fake_build_view(*, specialist_id, public_name, owner_tg_user_id):
        keyboard = owner_panel.InlineKeyboardMarkup(
            inline_keyboard=[
                [owner_panel.InlineKeyboardButton(text="📅", callback_data="owner_panel:calendar_menu")],
                [owner_panel.InlineKeyboardButton(text="⏱️", callback_data="owner_panel:change_duration_buffer")],
                [owner_panel.InlineKeyboardButton(text="⚙️", callback_data="owner_panel:slot_params_menu")],
                [owner_panel.InlineKeyboardButton(text="🌍", callback_data="owner_panel:change_timezone")],
                [owner_panel.InlineKeyboardButton(text="📅", callback_data="owner_panel:change_schedule")],
                [owner_panel.InlineKeyboardButton(text="♻️", callback_data="owner_panel:apply_defaults")],
            ]
        )
        return "owner panel", keyboard

    monkeypatch.setattr(owner_panel, "_ensure_owner_panel_defaults", fake_ensure_defaults)
    monkeypatch.setattr(owner_panel, "_build_owner_panel_view", fake_build_view)

    await owner_panel.send_owner_panel(
        message=first_open_message,
        specialist_id="sp-id",
        public_name="Dr. Test",
        owner_tg_user_id=123,
    )
    await owner_panel._render_owner_panel_inplace(
        message=back_message,
        specialist_id="sp-id",
        public_name="Dr. Test",
        owner_tg_user_id=123,
    )

    first_callbacks = [
        button.callback_data
        for row in first_open_message.answers[-1][1]["reply_markup"].inline_keyboard
        for button in row
        if button.callback_data
    ]
    back_callbacks = [
        button.callback_data
        for row in back_message.edits[-1][1]["reply_markup"].inline_keyboard
        for button in row
        if button.callback_data
    ]

    assert first_callbacks == back_callbacks
    assert "owner_panel:apply_defaults" in first_callbacks
