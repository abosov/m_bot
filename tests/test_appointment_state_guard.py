from types import SimpleNamespace

import pytest

from database import BookingState
from services.appointment_state_guard import (
    AppointmentOwnershipError,
    InvalidAppointmentTransitionError,
    approve_by_specialist,
    mark_google_create_failed,
    mark_google_create_succeeded,
    reject_by_specialist,
)


def _appointment(*, state: BookingState, specialist_id: str = "sp-1"):
    return SimpleNamespace(
        specialist_id=specialist_id,
        booking_state=state,
        gcal_event_id=None,
        failure_message=None,
        confirmed_at=None,
        rejected_at=None,
        rejection_reason=None,
    )


def test_google_create_success_transitions_pending_to_awaiting_specialist_confirmation():
    appt = _appointment(state=BookingState.pending)

    mark_google_create_succeeded(appt, specialist_id="sp-1", google_event_id="evt-1")

    assert appt.booking_state == BookingState.awaiting_specialist_confirmation
    assert appt.gcal_event_id == "evt-1"
    assert appt.failure_message is None


def test_google_create_error_transitions_pending_to_failed():
    appt = _appointment(state=BookingState.pending)

    mark_google_create_failed(appt, specialist_id="sp-1")

    assert appt.booking_state == BookingState.failed
    assert appt.failure_message == "google_error"


def test_specialist_approve_reject_allowed_only_from_awaiting():
    appt = _appointment(state=BookingState.awaiting_specialist_confirmation)

    result = approve_by_specialist(appt, specialist_id="sp-1")

    assert result == "updated"
    assert appt.booking_state == BookingState.confirmed

    bad = _appointment(state=BookingState.pending)
    with pytest.raises(InvalidAppointmentTransitionError):
        approve_by_specialist(bad, specialist_id="sp-1")


def test_specialist_idempotency_for_repeat_clicks():
    confirmed = _appointment(state=BookingState.confirmed)
    assert approve_by_specialist(confirmed, specialist_id="sp-1") == "already_processed"
    assert reject_by_specialist(confirmed, specialist_id="sp-1") == "already_processed"

    rejected = _appointment(state=BookingState.rejected_by_specialist)
    assert approve_by_specialist(rejected, specialist_id="sp-1") == "already_processed"
    assert reject_by_specialist(rejected, specialist_id="sp-1") == "already_processed"


def test_specialist_ownership_is_required():
    appt = _appointment(state=BookingState.pending, specialist_id="sp-2")

    with pytest.raises(AppointmentOwnershipError):
        mark_google_create_succeeded(appt, specialist_id="sp-1", google_event_id="evt-1")
