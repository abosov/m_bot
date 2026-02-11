from handlers.personal_bot.routers.specialist import owner_panel


def test_slot_step_allowed_values() -> None:
    assert owner_panel._ALLOWED_SLOT_STEPS_MIN == {60, 30, 15, 10}


def test_slot_step_default_is_15() -> None:
    assert owner_panel._DEFAULT_SLOT_STEP_MIN == 15
