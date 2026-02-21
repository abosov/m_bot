from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Appointment, AppointmentCalendarLink, SpecialistCalendarSettings
from services.appointment_state_guard import (
    InvalidAppointmentTransitionError,
    approve_by_specialist,
    reject_by_specialist,
)
from services.google_calendar import GoogleCalendarError, delete_appointment_event
from services.outbox import emit_domain_event


ConfirmBySpecialistStatus = Literal["ok", "updated", "already_processed", "invalid_state", "not_found"]


@dataclass(frozen=True)
class SpecialistAppointmentConfirmationResult:
    status: ConfirmBySpecialistStatus
    appointment: Appointment | None


class SpecialistAppointmentRejectCalendarDeleteError(RuntimeError):
    """Raised when specialist rejection cannot delete the linked Google Calendar event."""


async def confirm_by_specialist(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
) -> SpecialistAppointmentConfirmationResult:
    async with session.begin():
        result = await session.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .with_for_update()
        )
        appointment = result.scalar_one_or_none()
        if appointment is None or str(appointment.specialist_id) != str(specialist_id):
            return SpecialistAppointmentConfirmationResult(status="not_found", appointment=None)

        try:
            transition_result = approve_by_specialist(appointment, specialist_id)
        except InvalidAppointmentTransitionError:
            return SpecialistAppointmentConfirmationResult(status="invalid_state", appointment=appointment)

        if transition_result == "already_processed":
            return SpecialistAppointmentConfirmationResult(status="already_processed", appointment=appointment)

        await emit_domain_event(
            session,
            "appointment_confirmed_by_specialist",
            {
                "appointment_id": str(appointment.appointment_id),
                "specialist_id": str(appointment.specialist_id),
                "client_id": str(appointment.client_id),
                "start_at_utc": appointment.start_at_utc.astimezone(timezone.utc).isoformat(),
                "end_at_utc": appointment.end_at_utc.astimezone(timezone.utc).isoformat(),
            },
        )

    return SpecialistAppointmentConfirmationResult(status="ok", appointment=appointment)


async def confirm_appointment_by_specialist(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
) -> SpecialistAppointmentConfirmationResult:
    return await confirm_by_specialist(
        session,
        appointment_id=appointment_id,
        specialist_id=specialist_id,
    )


async def reject_appointment_by_specialist(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
    rejection_reason: str | None = None,
) -> SpecialistAppointmentConfirmationResult:
    async with session.begin():
        result = await session.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .with_for_update()
        )
        appointment = result.scalar_one_or_none()
        if appointment is None or str(appointment.specialist_id) != str(specialist_id):
            return SpecialistAppointmentConfirmationResult(status="not_found", appointment=None)

        result = reject_by_specialist(appointment, specialist_id, rejection_reason=rejection_reason)
        if result == "already_processed":
            return SpecialistAppointmentConfirmationResult(status="already_processed", appointment=appointment)

        event_identifiers = await _resolve_google_event_identifiers(
            session,
            appointment_id=appointment.appointment_id,
            specialist_id=appointment.specialist_id,
            fallback_google_event_id=appointment.gcal_event_id,
        )
        if event_identifiers is not None:
            calendar_id, google_event_id = event_identifiers
            try:
                await delete_appointment_event(
                    specialist_id=appointment.specialist_id,
                    calendar_id=calendar_id,
                    google_event_id=google_event_id,
                )
            except GoogleCalendarError as exc:
                # 404 => already deleted in Google Calendar, treat as idempotent success.
                if "status 404" not in str(exc).lower() and "not found" not in str(exc).lower():
                    raise SpecialistAppointmentRejectCalendarDeleteError(
                        "failed to delete appointment Google Calendar event"
                    ) from exc

        payload = {
            "appointment_id": str(appointment.appointment_id),
            "specialist_id": str(appointment.specialist_id),
            "client_id": str(appointment.client_id),
            "start_at_utc": appointment.start_at_utc.astimezone(timezone.utc).isoformat(),
            "end_at_utc": appointment.end_at_utc.astimezone(timezone.utc).isoformat(),
        }
        if rejection_reason is not None:
            payload["rejection_reason"] = rejection_reason

        await emit_domain_event(
            session,
            "appointment_rejected_by_specialist",
            payload,
        )

    return SpecialistAppointmentConfirmationResult(status="updated", appointment=appointment)


async def _resolve_google_event_identifiers(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
    fallback_google_event_id: str | None,
) -> tuple[str, str] | None:
    link = await session.get(AppointmentCalendarLink, appointment_id)
    if link is not None and link.calendar_id and link.google_event_id:
        return link.calendar_id, link.google_event_id

    if not fallback_google_event_id:
        return None

    settings = await session.get(SpecialistCalendarSettings, specialist_id)
    calendar_id = settings.calendar_id if settings is not None else None
    if not calendar_id:
        return None
    return calendar_id, fallback_google_event_id
