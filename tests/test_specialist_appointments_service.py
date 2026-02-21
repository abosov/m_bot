from datetime import datetime, timezone
from uuid import uuid4

import pytest

from database import Appointment, BookingState
from services import specialist_appointments


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


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

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

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

    assert result.status == "ok"
    assert appointment.booking_state == BookingState.confirmed
    assert emitted[0][1] == "appointment_confirmed_by_specialist"


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_is_idempotent(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.confirmed,
        idempotency_key="idk",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

    emitted = []

    async def fake_emit(*args, **kwargs):
        emitted.append((args, kwargs))

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)

    result = await specialist_appointments.confirm_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
    )

    assert result.status == "already_processed"
    assert emitted == []


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_returns_invalid_state():
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.pending,
        idempotency_key="idk",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

    result = await specialist_appointments.confirm_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
    )

    assert result.status == "invalid_state"


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_returns_not_found():
    class _Result:
        def scalar_one_or_none(self):
            return None

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

    result = await specialist_appointments.confirm_appointment_by_specialist(
        Session(),
        appointment_id=uuid4(),
        specialist_id=uuid4(),
    )

    assert result.status == "not_found"


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
        gcal_event_id="ev-1",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, key):
            if model.__name__ == "AppointmentCalendarLink":
                return None
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

    emitted = []
    deleted = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    async def fake_delete(**kwargs):
        deleted.append(kwargs)

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)

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
    assert appointment.gcal_event_id is None
    assert deleted[0]["calendar_id"] == "cal-1"
    assert emitted[0][1] == "appointment_rejected_by_specialist"
    assert emitted[0][2]["rejection_reason"] == "Не смогу"


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_continues_when_google_delete_failed(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
        gcal_event_id="ev-1",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, key):
            if model.__name__ == "AppointmentCalendarLink":
                return None
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

    async def fake_delete(**_kwargs):
        raise specialist_appointments.GoogleCalendarError("Google Calendar API failed with status 500")

    alerts = []

    async def fake_notify(event):
        alerts.append(event)

    async def fake_emit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)
    monkeypatch.setattr(specialist_appointments, "notify_admin", fake_notify)
    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "updated"
    assert appointment.booking_state == BookingState.rejected_by_specialist
    assert appointment.gcal_event_id == "ev-1"
    assert alerts


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_treats_google_404_as_success(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
        gcal_event_id="ev-1",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, key):
            if model.__name__ == "AppointmentCalendarLink":
                return None
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

    emitted = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    async def fake_delete(**_kwargs):
        raise specialist_appointments.GoogleCalendarError("Google Calendar API failed with status 404")

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "updated"
    assert appointment.gcal_event_id is None
    assert emitted[0][2].get("rejection_reason") is None


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_is_idempotent(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.rejected_by_specialist,
        idempotency_key="idk",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

    emitted = []
    deleted = []

    async def fake_emit(*args, **kwargs):
        emitted.append((args, kwargs))

    async def fake_delete(**kwargs):
        deleted.append(kwargs)

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "already_processed"
    assert emitted == []
    assert deleted == []


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_without_reason_emits_event_without_reason(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
        gcal_event_id="ev-1",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, key):
            if model.__name__ == "AppointmentCalendarLink":
                return None
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

    emitted = []
    deleted = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    async def fake_delete(**kwargs):
        deleted.append(kwargs)

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "updated"
    assert appointment.rejection_reason is None
    assert deleted[0]["calendar_id"] == "cal-1"
    assert emitted[0][1] == "appointment_rejected_by_specialist"
    assert "rejection_reason" not in emitted[0][2]


@pytest.mark.asyncio
async def test_confirm_appointment_by_specialist_logs_decision(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

    logged = []

    async def fake_emit(*_args, **_kwargs):
        return None

    def fake_log_event(*_args, **kwargs):
        logged.append(kwargs)

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "log_event", fake_log_event)

    result = await specialist_appointments.confirm_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
    )

    assert result.status == "ok"
    assert logged[-1]["action"] == "confirm"
    assert logged[-1]["result"] == "ok"


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_sends_alert_on_google_delete_error(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
        gcal_event_id="ev-1",
    )

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, _key):
            if model.__name__ == "AppointmentCalendarLink":
                return None
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

    async def fake_delete(**_kwargs):
        raise specialist_appointments.GoogleCalendarError("Google Calendar API failed with status 500")

    alerts = []

    async def fake_notify(event):
        alerts.append(event)

    async def fake_emit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)
    monkeypatch.setattr(specialist_appointments, "notify_admin", fake_notify)
    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)

    result = await specialist_appointments.reject_appointment_by_specialist(
        Session(),
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason=None,
    )

    assert result.status == "updated"
    assert alerts
    assert alerts[0].title == "Google Calendar delete failed"
    assert alerts[0].context["appointment_id"] == str(appointment.appointment_id)


@pytest.mark.asyncio
async def test_reject_appointment_by_specialist_clears_calendar_link_after_google_delete(monkeypatch):
    appointment = Appointment(
        appointment_id=uuid4(),
        specialist_id=uuid4(),
        client_id=uuid4(),
        start_at_utc=datetime.now(timezone.utc),
        end_at_utc=datetime.now(timezone.utc),
        booking_state=BookingState.awaiting_specialist_confirmation,
        idempotency_key="idk",
        gcal_event_id="ev-1",
    )
    link = type("Link", (), {"calendar_id": "cal-1", "google_event_id": "ev-1"})()

    class _Result:
        def scalar_one_or_none(self):
            return appointment

    class Session:
        def __init__(self):
            self.deleted = []

        def begin(self):
            return _Begin()

        async def execute(self, _query):
            return _Result()

        async def get(self, model, _key):
            if model.__name__ == "AppointmentCalendarLink":
                return link
            if model.__name__ == "SpecialistCalendarSettings":
                return type("Settings", (), {"calendar_id": "cal-1"})()
            raise AssertionError(model)

        async def delete(self, obj):
            self.deleted.append(obj)

    emitted = []
    deleted_events = []

    async def fake_emit(session, event_type, payload):
        emitted.append((session, event_type, payload))

    async def fake_delete(**kwargs):
        deleted_events.append(kwargs)

    monkeypatch.setattr(specialist_appointments, "emit_domain_event", fake_emit)
    monkeypatch.setattr(specialist_appointments, "delete_appointment_event", fake_delete)

    session = Session()
    result = await specialist_appointments.reject_appointment_by_specialist(
        session,
        appointment_id=appointment.appointment_id,
        specialist_id=appointment.specialist_id,
        rejection_reason="Нет окна",
    )

    assert result.status == "updated"
    assert appointment.booking_state == BookingState.rejected_by_specialist
    assert appointment.gcal_event_id is None
    assert deleted_events and deleted_events[0]["google_event_id"] == "ev-1"
    assert session.deleted == [link]
    assert emitted[0][1] == "appointment_rejected_by_specialist"
