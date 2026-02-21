from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from database import Appointment
from services.appointment_state_guard import approve_by_specialist, reject_by_specialist
from services.outbox import emit_domain_event


@dataclass(frozen=True)
class SpecialistAppointmentConfirmationResult:
    status: str
    appointment: Appointment | None


async def confirm_appointment_by_specialist(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
) -> SpecialistAppointmentConfirmationResult:
    appointment = await session.get(Appointment, appointment_id)
    if appointment is None or str(appointment.specialist_id) != str(specialist_id):
        return SpecialistAppointmentConfirmationResult(status="not_found", appointment=None)

    result = approve_by_specialist(appointment, specialist_id)
    if result == "already_processed":
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
    await session.commit()
    return SpecialistAppointmentConfirmationResult(status="updated", appointment=appointment)


async def reject_appointment_by_specialist(
    session: AsyncSession,
    *,
    appointment_id: UUID,
    specialist_id,
    rejection_reason: str | None = None,
) -> SpecialistAppointmentConfirmationResult:
    appointment = await session.get(Appointment, appointment_id)
    if appointment is None or str(appointment.specialist_id) != str(specialist_id):
        return SpecialistAppointmentConfirmationResult(status="not_found", appointment=None)

    result = reject_by_specialist(appointment, specialist_id, rejection_reason=rejection_reason)
    if result == "already_processed":
        return SpecialistAppointmentConfirmationResult(status="already_processed", appointment=appointment)

    await emit_domain_event(
        session,
        "appointment_rejected_by_specialist",
        {
            "appointment_id": str(appointment.appointment_id),
            "specialist_id": str(appointment.specialist_id),
            "client_id": str(appointment.client_id),
            "start_at_utc": appointment.start_at_utc.astimezone(timezone.utc).isoformat(),
            "end_at_utc": appointment.end_at_utc.astimezone(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason,
        },
    )
    await session.commit()
    return SpecialistAppointmentConfirmationResult(status="updated", appointment=appointment)
