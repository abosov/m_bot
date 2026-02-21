from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from database import Appointment, BookingState


class InvalidAppointmentTransitionError(ValueError):
    """Raised when requested booking_state transition is not allowed."""


class AppointmentOwnershipError(ValueError):
    """Raised when appointment does not belong to the acting specialist."""


IdempotentResult = Literal["updated", "already_processed"]


@dataclass(frozen=True)
class TransitionRule:
    from_state: BookingState
    to_state: BookingState


_ALLOWED_TRANSITIONS: tuple[TransitionRule, ...] = (
    TransitionRule(BookingState.pending, BookingState.awaiting_specialist_confirmation),
    TransitionRule(BookingState.pending, BookingState.failed),
    TransitionRule(BookingState.awaiting_specialist_confirmation, BookingState.confirmed),
    TransitionRule(BookingState.awaiting_specialist_confirmation, BookingState.rejected_by_specialist),
)


def ensure_specialist_ownership(appointment: Appointment, specialist_id) -> None:
    if str(appointment.specialist_id) != str(specialist_id):
        raise AppointmentOwnershipError("appointment does not belong to specialist")


def apply_transition(appointment: Appointment, to_state: BookingState) -> None:
    is_allowed = any(
        rule.from_state == appointment.booking_state and rule.to_state == to_state
        for rule in _ALLOWED_TRANSITIONS
    )
    if not is_allowed:
        raise InvalidAppointmentTransitionError(
            f"transition {appointment.booking_state.value} -> {to_state.value} is not allowed"
        )
    appointment.booking_state = to_state


def mark_google_create_succeeded(appointment: Appointment, specialist_id, google_event_id: str | None) -> None:
    ensure_specialist_ownership(appointment, specialist_id)
    apply_transition(appointment, BookingState.awaiting_specialist_confirmation)
    appointment.gcal_event_id = google_event_id
    appointment.failure_message = None


def mark_google_create_failed(appointment: Appointment, specialist_id, failure_message: str = "google_error") -> None:
    ensure_specialist_ownership(appointment, specialist_id)
    apply_transition(appointment, BookingState.failed)
    appointment.failure_message = failure_message


def approve_by_specialist(appointment: Appointment, specialist_id) -> IdempotentResult:
    ensure_specialist_ownership(appointment, specialist_id)
    if appointment.booking_state in (BookingState.confirmed, BookingState.rejected_by_specialist):
        return "already_processed"
    apply_transition(appointment, BookingState.confirmed)
    appointment.confirmed_at = datetime.now(timezone.utc)
    appointment.rejected_at = None
    appointment.rejection_reason = None
    return "updated"


def reject_by_specialist(appointment: Appointment, specialist_id, *, rejection_reason: str | None = None) -> IdempotentResult:
    ensure_specialist_ownership(appointment, specialist_id)
    if appointment.booking_state in (BookingState.confirmed, BookingState.rejected_by_specialist):
        return "already_processed"
    apply_transition(appointment, BookingState.rejected_by_specialist)
    appointment.rejected_at = datetime.now(timezone.utc)
    appointment.rejection_reason = rejection_reason
    return "updated"
