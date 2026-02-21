from datetime import datetime, timezone
from uuid import uuid4

import pytest

from database import Appointment, BookingState
from services import specialist_appointments


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_marks_updated(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
    )

    class Session:
        committed = False

        async def get(self, model, key):
            assert model.__name__ == "Appointment"
            assert key == appointment.appointment_id
            return appointment

        async def commit(self):
            self.committed = True

    emitted = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)

    session = Session()
    result = await specialist_appointments.confirm_appointment_by_specialist(
        session,
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
    )

    assert result.status == "updated"
    assert appointment.booking_state == BookingState.confirmed
    assert session.committed is True
    assert emitted[0][1] == "appointment_confirmed_by_specialist"


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_is_idempotent():
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.confirmed,
        idempotency_key="idk",
    )

    class Session:
        async def get(self, _model, _key):
            return appointment

    result = await specialist_appointments.confirm_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
    )

    assert result.status == "already_processed"


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_marks_updated(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
    )

    class Session:
        committed = False

        async def get(self, model, key):
            assert model.__name__ == "Appointment"
            assert key == appointment.appointment_id
            return appointment

        async def commit(self):
            self.committed = True

    emitted = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)

    session = Session()
    result = await specialist_appointments.reject_appointment_by_specialist(
        session,
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason="Не смогу",
    )

    assert result.status == "updated"
    assert appointment.booking_state == BookingState.rejected_by_specialist
    assert appointment.rejection_reason == "Не смогу"
    assert session.committed is True
    assert emitted[0][1] == "appointment_rejected_by_specialist"


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_is_idempotent():
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.rejected_by_specialist,
        idempotency_key="idk",
    )

    class Session:
        async def get(self, _model, _key):
            return appointment

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "already_processed"
