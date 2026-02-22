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

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class DummyCallback:
    def __init__(self):
        self.message = DummyMessage()
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_apply_defaults_uses_expected_profile_defaults(monkeypatch) -> None:
    captured = {}

    async def fake_update_profile_settings(**kwargs):
        captured["profile"] = kwargs

    async def fake_apply_weekly_defaults(**kwargs):
        captured["weekly"] = kwargs

    async def fake_send_owner_panel(*args, **kwargs):
        captured["owner_panel"] = {"args": args, "kwargs": kwargs}

    monkeypatch.setattr(owner_panel, "_update_profile_settings", fake_update_profile_settings)
    monkeypatch.setattr(owner_panel, "_apply_weekly_defaults", fake_apply_weekly_defaults)
    monkeypatch.setattr(owner_panel, "send_owner_panel", fake_send_owner_panel)

    callback = DummyCallback()

    await owner_panel.owner_panel_apply_defaults(
        callback=callback,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. House",
    )

    assert captured["profile"]["session_duration_min"] == 60
    assert captured["profile"]["session_buffer_min"] == 10
    assert captured["profile"]["max_sessions_per_day"] == 4
    assert captured["profile"]["slot_step_min"] == 15

    assert captured["weekly"]["interval_1"] == (time(9, 0), time(12, 0))
    assert captured["weekly"]["interval_2"] == (time(13, 0), time(17, 0))
    assert captured["weekly"]["interval_3"] == (time(17, 0), time(21, 0))


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
    keyboard = owner_panel._owner_panel_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "owner_panel:calendar_menu" in callbacks


@pytest.mark.asyncio
async def test_owner_cal_create_returns_soft_refusal_and_calendar_menu() -> None:
    callback = DummyCallback()

    await owner_panel.owner_calendar_create(
        callback=callback,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert len(callback.message.answers) == 2
    assert callback.message.answers[0][0] == (
        "ℹ️ Сейчас Zumbot подключается только к уже существующему календарю Google.\n"
        "Если нужен отдельный календарь — создайте его вручную в Google Calendar, затем выберите в боте."
    )
    assert callback.message.answers[1][0] == "Выберите действие с календарём:"
    keyboard = callback.message.answers[1][1]["reply_markup"]
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

    profile = type("Profile", (), {"session_duration_min": 60})()

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
    assert state.current_state == owner_panel.LimitsSettingsStates.waiting_max_sessions

    first_message.text = "12"
    await owner_panel.owner_panel_receive_max_sessions(first_message, state=state, specialist_id="sp-id")
    assert state.current_state == owner_panel.LimitsSettingsStates.waiting_slot_step

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
    state.data = {"limits_max_sessions_candidate": 8, "limits_duration_min": 30}

    called = {"update": 0}

    async def fake_update_limits(*args, **kwargs):
        called["update"] += 1
        return {}

    monkeypatch.setattr(owner_panel, "update_limits", fake_update_limits)

    message.text = "35"
    await owner_panel.owner_panel_receive_slot_step(
        message,
        state=state,
        specialist_id="sp-id",
        owner_tg_user_id=123,
        public_name="Dr. Test",
    )

    assert "не может быть больше длительности" in message.answers[-1][0]
    assert called == {"update": 0}
