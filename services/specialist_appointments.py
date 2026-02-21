from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Appointment
from services.appointment_state_guard import (
    InvalidAppointmentTransitionError,
    approve_by_specialist,
    reject_by_specialist,
)
from services.outbox import emit_domain_event


ConfirmBySpecialistStatus = Literal["ok", "updated", "already_processed", "invalid_state", "not_found"]


@dataclass(frozen=True)
class SpecialistAppointmentConfirmationResult:
    status: ConfirmBySpecialistStatus
    appointment: Appointment | None


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
