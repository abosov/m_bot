import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, select

import config

import requests

from database import Appointment, AppointmentCalendarLink, BookingState, CalendarSyncState, async_session_factory
from services.outbox import emit_domain_event as emit_outbox_domain_event

logger = logging.getLogger(__name__)
GOOGLE_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3"


class ReconcileOutcome(str, Enum):
    UPDATED = "updated"
    NOOP = "noop"
    REJECTED = "rejected"


@dataclass(slots=True)
class ReconcileResult:
    result: ReconcileOutcome
    reason: str | None = None
    appointment_id: uuid.UUID | None = None


def _parse_event_datetime(value: dict[str, Any] | None) -> datetime | None:
    if not isinstance(value, dict):
        return None

    date_time_raw = value.get("dateTime")
    if not date_time_raw:
        return None

    try:
        parsed = datetime.fromisoformat(str(date_time_raw).replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        tz_name = value.get("timeZone")
        if not tz_name:
            return None
        from zoneinfo import ZoneInfo

        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(str(tz_name)))
        except Exception:
            return None

    return parsed.astimezone(timezone.utc)


class GoogleCalendarSyncTokenInvalidError(Exception):
    pass


def _is_appointment_cancelled(booking_state: BookingState) -> bool:
    return booking_state in {BookingState.canceled_by_client, BookingState.canceled_by_specialist}


def _is_appointment_active_for_reverse_sync(booking_state: BookingState) -> bool:
    return booking_state in {BookingState.confirmed, BookingState.awaiting_specialist_confirmation}


def _extract_appointment_id(event: dict[str, Any]) -> uuid.UUID | None:
    appointment_id_raw = (
        event.get("extendedProperties", {})
        .get("private", {})
        .get("zumbot_appointment_id")
    )
    if not appointment_id_raw:
        return None
    try:
        return uuid.UUID(str(appointment_id_raw))
    except (ValueError, TypeError):
        return None


def _parse_google_updated(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _list_events_page(
    specialist_id: uuid.UUID,
    calendar_id: str,
    headers: dict[str, str],
    *,
    sync_token: str | None,
    page_token: str | None,
) -> dict[str, Any]:
    from services.google_calendar import _calendar_request_with_retry, _raise_calendar_error

    params: dict[str, Any] = {"showDeleted": "true", "maxResults": 250}
    if sync_token:
        params["syncToken"] = sync_token
    if page_token:
        params["pageToken"] = page_token

    response = await _calendar_request_with_retry(
        requests.get,
        f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events",
        method_name="GET",
        headers=headers,
        params=params,
    )
    if response.status_code == 410:
        raise GoogleCalendarSyncTokenInvalidError("sync token invalid")
    if response.status_code != 200:
        _raise_calendar_error(response)
    payload = response.json()
    logger.info(
        "event=google_calendar_reverse_sync_events_page specialist_id=%s calendar_id=%s sync_mode=%s events_count=%s",
        specialist_id,
        calendar_id,
        "incremental" if sync_token else "full",
        len(payload.get("items", [])),
    )
    return payload


async def reconcile_event_to_appointment(
    event: dict[str, Any],
    specialist_id: uuid.UUID,
    calendar_id: str,
) -> ReconcileResult:
    appointment_id = _extract_appointment_id(event)
    if appointment_id is None:
        return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="missing_appointment_id")

    async with async_session_factory() as session:
        appointment = await session.get(Appointment, appointment_id)
        if appointment is None:
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="appointment_not_found", appointment_id=appointment_id)
        if appointment.specialist_id != specialist_id:
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="specialist_mismatch", appointment_id=appointment_id)

        if event.get("status") == "cancelled":
            if _is_appointment_cancelled(appointment.booking_state):
                return ReconcileResult(result=ReconcileOutcome.NOOP, appointment_id=appointment_id)
            if not _is_appointment_active_for_reverse_sync(appointment.booking_state):
                return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="inactive_booking_state", appointment_id=appointment_id)

            appointment.booking_state = BookingState.canceled_by_specialist
            payload = {
                    "appointment_id": str(appointment_id),
                    "specialist_id": str(specialist_id),
                    "client_id": str(appointment.client_id),
                    "calendar_id": calendar_id,
                    "google_event_id": str(event.get("id") or ""),
                }
            await emit_outbox_domain_event(session, "appointment_cancelled_by_specialist_calendar", payload)
            logger.info("event=domain_event_enqueued event_type=%s payload=%s", "appointment_cancelled_by_specialist_calendar", payload)
            await session.commit()
            return ReconcileResult(result=ReconcileOutcome.UPDATED, appointment_id=appointment_id)

        if not _is_appointment_active_for_reverse_sync(appointment.booking_state):
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="inactive_booking_state", appointment_id=appointment_id)

        start_at_utc = _parse_event_datetime(event.get("start"))
        end_at_utc = _parse_event_datetime(event.get("end"))
        if start_at_utc is None or end_at_utc is None or end_at_utc <= start_at_utc:
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="invalid_event_time", appointment_id=appointment_id)

        if appointment.start_at_utc == start_at_utc and appointment.end_at_utc == end_at_utc:
            return ReconcileResult(result=ReconcileOutcome.NOOP, appointment_id=appointment_id)

        min_notice_hours = config.APPOINTMENT_RESCHEDULE_MIN_NOTICE_HOURS
        now_utc = datetime.now(timezone.utc)
        if appointment.start_at_utc - now_utc < timedelta(hours=min_notice_hours):
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="min_notice_violation", appointment_id=appointment_id)

        conflict_stmt = select(Appointment.appointment_id).where(
            and_(
                Appointment.specialist_id == specialist_id,
                Appointment.appointment_id != appointment_id,
                Appointment.booking_state == BookingState.confirmed,
                Appointment.start_at_utc < end_at_utc,
                Appointment.end_at_utc > start_at_utc,
            )
        ).limit(1)
        conflict_exists = (await session.execute(conflict_stmt)).scalar_one_or_none() is not None
        if conflict_exists:
            return ReconcileResult(result=ReconcileOutcome.REJECTED, reason="time_conflict", appointment_id=appointment_id)

        old_start_at_utc = appointment.start_at_utc
        appointment.start_at_utc = start_at_utc
        appointment.end_at_utc = end_at_utc
        if hasattr(BookingState, "rescheduled"):
            appointment.booking_state = BookingState.rescheduled

        payload = {
                "appointment_id": str(appointment_id),
                "specialist_id": str(specialist_id),
                "client_id": str(appointment.client_id),
                "calendar_id": calendar_id,
                "old_start_at_utc": old_start_at_utc.isoformat(),
                "new_start_at_utc": start_at_utc.isoformat(),
                "start_at_utc": start_at_utc.isoformat(),
                "end_at_utc": end_at_utc.isoformat(),
            }
        await emit_outbox_domain_event(session, "appointment_rescheduled", payload)
        logger.info("event=domain_event_enqueued event_type=%s payload=%s", "appointment_rescheduled", payload)
        await session.commit()
        return ReconcileResult(result=ReconcileOutcome.UPDATED, appointment_id=appointment_id)


async def run_calendar_reverse_sync(specialist_id: uuid.UUID, calendar_id: str) -> None:
    from services.google_calendar import _build_headers

    headers = await _build_headers(specialist_id)

    async with async_session_factory() as session:
        sync_state = await session.get(CalendarSyncState, {"specialist_id": specialist_id, "calendar_id": calendar_id})
        if sync_state is None:
            sync_state = CalendarSyncState(specialist_id=specialist_id, calendar_id=calendar_id)
            session.add(sync_state)

        events: list[dict[str, Any]] = []
        next_sync_token: str | None = None
        current_sync_token = sync_state.sync_token

        try:
            page_token = None
            try:
                while True:
                    payload = await _list_events_page(
                        specialist_id,
                        calendar_id,
                        headers,
                        sync_token=current_sync_token,
                        page_token=page_token,
                    )
                    events.extend(payload.get("items", []))
                    page_token = payload.get("nextPageToken")
                    next_sync_token = payload.get("nextSyncToken") or next_sync_token
                    if not page_token:
                        break
            except GoogleCalendarSyncTokenInvalidError:
                logger.warning(
                    "event=google_calendar_reverse_sync_sync_token_invalid specialist_id=%s calendar_id=%s",
                    specialist_id,
                    calendar_id,
                )
                events = []
                page_token = None
                next_sync_token = None
                while True:
                    payload = await _list_events_page(
                        specialist_id,
                        calendar_id,
                        headers,
                        sync_token=None,
                        page_token=page_token,
                    )
                    events.extend(payload.get("items", []))
                    page_token = payload.get("nextPageToken")
                    next_sync_token = payload.get("nextSyncToken") or next_sync_token
                    if not page_token:
                        break

            now = datetime.now(timezone.utc)
            for event in events:
                appointment_id = _extract_appointment_id(event)
                google_event_id = event.get("id")
                if not appointment_id:
                    logger.info(
                        "event=google_calendar_reverse_sync_ignore_event_without_appointment specialist_id=%s calendar_id=%s google_event_id=%s appointment_id=%s",
                        specialist_id,
                        calendar_id,
                        google_event_id,
                        None,
                    )
                    continue

                link = await session.get(AppointmentCalendarLink, appointment_id)

                event_updated = _parse_google_updated(event.get("updated"))
                event_etag = event.get("etag")
                if (
                    link is not None
                    and link.calendar_id == calendar_id
                    and link.google_event_id == google_event_id
                    and link.event_etag == event_etag
                    and link.event_updated == event_updated
                ):
                    logger.info(
                        "event=google_calendar_reverse_sync_skip_duplicate specialist_id=%s calendar_id=%s google_event_id=%s appointment_id=%s",
                        specialist_id,
                        calendar_id,
                        google_event_id,
                        appointment_id,
                    )
                    continue

                reconcile_result = await reconcile_event_to_appointment(event, specialist_id, calendar_id)

                if reconcile_result.result == ReconcileOutcome.REJECTED:
                    logger.info(
                        "event=google_calendar_reverse_sync_rejected specialist_id=%s calendar_id=%s google_event_id=%s appointment_id=%s reason=%s",
                        specialist_id,
                        calendar_id,
                        google_event_id,
                        appointment_id,
                        reconcile_result.reason,
                    )
                    continue

                if reconcile_result.result not in {ReconcileOutcome.UPDATED, ReconcileOutcome.NOOP}:
                    continue

                if link is None:
                    link = AppointmentCalendarLink(
                        appointment_id=appointment_id,
                        specialist_id=specialist_id,
                        calendar_id=calendar_id,
                        google_event_id=google_event_id,
                    )
                    session.add(link)

                link.specialist_id = specialist_id
                link.calendar_id = calendar_id
                link.google_event_id = google_event_id
                link.ical_uid = event.get("iCalUID")
                link.event_etag = event_etag
                link.event_updated = event_updated
                link.last_synced_at = now

                logger.info(
                    "event=google_calendar_reverse_sync_link_updated specialist_id=%s calendar_id=%s google_event_id=%s appointment_id=%s",
                    specialist_id,
                    calendar_id,
                    google_event_id,
                    appointment_id,
                )

            sync_state.sync_token = next_sync_token
            sync_state.last_success_at = now
            sync_state.error_count = 0
            await session.commit()
        except Exception:
            sync_state.last_error_at = datetime.now(timezone.utc)
            sync_state.error_count = (sync_state.error_count or 0) + 1
            await session.commit()
            raise
