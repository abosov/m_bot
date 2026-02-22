from datetime import time

import pytest

from handlers.personal_bot.routers.specialist import owner_panel


def test_slot_step_allowed_values() -> None:
    assert owner_panel._ALLOWED_SLOT_STEPS_MIN == {60, 30, 15, 10}


def test_slot_step_default_is_15() -> None:
    assert owner_panel._DEFAULT_SLOT_STEP_MIN == 15


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
        "Если вам нужен отдельный календарь — создайте его вручную в Google Calendar, затем нажмите «📂 Выбрать существующий»."
    )
    assert callback.message.answers[1][0] == "Выберите действие с календарём:"
    keyboard = callback.message.answers[1][1]["reply_markup"]
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks == ["owner_cal:select", "owner_cal:smoke", "owner_cal:back"]
