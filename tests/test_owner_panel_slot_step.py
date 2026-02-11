from datetime import time

import pytest

from handlers.personal_bot.routers.specialist import owner_panel


def test_slot_step_allowed_values() -> None:
    assert owner_panel._ALLOWED_SLOT_STEPS_MIN == {60, 30, 15, 10}


def test_slot_step_default_is_15() -> None:
    assert owner_panel._DEFAULT_SLOT_STEP_MIN == 15


def test_validate_interval_pair_allows_both_null() -> None:
    owner_panel._validate_interval_pair(start=None, end=None)


def test_validate_interval_pair_rejects_half_filled_pair() -> None:
    with pytest.raises(owner_panel.AvailabilityValidationError):
        owner_panel._validate_interval_pair(start=time(9, 0), end=None)


def test_validate_interval_pair_rejects_non_positive_interval() -> None:
    with pytest.raises(owner_panel.AvailabilityValidationError):
        owner_panel._validate_interval_pair(start=time(12, 0), end=time(12, 0))
