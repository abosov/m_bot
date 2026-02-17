import logging
import asyncio
import random
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import select

import config
from database import GoogleOAuth, async_session_factory
from services.crypto import decrypt_token
from services.alerting import notify_exception
from services.log_context import log_event

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3"

logger = logging.getLogger(__name__)

_RETRY_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 0.2
_RETRY_MAX_DELAY_SECONDS = 1.0
_RETRY_MAX_TOTAL_SECONDS = 2.0


class GoogleCalendarError(Exception):
    pass


class GoogleCalendarInsufficientPermissionsError(GoogleCalendarError):
    pass


class GoogleCalendarAuthError(GoogleCalendarError):
    pass


async def _notify_google_calendar_exception(where: str, exc: Exception, specialist_id: uuid.UUID | None = None) -> None:
    if isinstance(exc, GoogleCalendarInsufficientPermissionsError):
        return
    await notify_exception(
        where=where,
        exc=exc,
        context={"specialist_id": str(specialist_id)} if specialist_id else None,
        stage="google_oauth",
    )


def required_scopes() -> list[str]:
    return [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]


def scopes_as_string() -> str:
    return " ".join(required_scopes())


async def _get_refresh_token(specialist_id: uuid.UUID) -> str:
    async with async_session_factory() as session:
        stmt = select(GoogleOAuth).where(GoogleOAuth.specialist_id == specialist_id)
        oauth_entry = (await session.execute(stmt)).scalar_one_or_none()
        if not oauth_entry:
            raise GoogleCalendarAuthError("Google OAuth not connected")
        return decrypt_token(oauth_entry.refresh_token_encrypted)


async def _build_headers(specialist_id: uuid.UUID) -> dict[str, str]:
    refresh_token = await _get_refresh_token(specialist_id)

    started = time.monotonic()
    response = await asyncio.to_thread(
        requests.post,
        GOOGLE_TOKEN_URL,
        data={
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    log_event(
        logger,
        logging.INFO,
        event="google_api_call",
        alias="oauth_refresh_token",
        duration_ms=int((time.monotonic() - started) * 1000),
        outcome="ok" if response.status_code == 200 else "error",
        http_status=response.status_code,
        specialist_id=specialist_id,
    )

    if response.status_code != 200:
        raise GoogleCalendarAuthError("Cannot refresh Google access token")

    access_token = response.json().get("access_token")
    if not access_token:
        raise GoogleCalendarAuthError("Google access token is missing")

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _raise_calendar_error(response: requests.Response) -> None:
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
    except Exception:
        message = response.text[:200]

    if response.status_code in (401, 403):
        text = message or "insufficientPermissions"
        if "insufficient" in text.lower() or response.status_code == 403:
            raise GoogleCalendarInsufficientPermissionsError(text)
        raise GoogleCalendarAuthError(text)

    raise GoogleCalendarError(message or f"Google Calendar API failed with status {response.status_code}")


async def _calendar_request_with_retry(
    request_callable,
    url: str,
    *,
    method_name: str,
    timeout: int = 10,
    **kwargs,
) -> requests.Response:
    start = time.monotonic()
    attempt = 1

    while True:
        try:
            response = await asyncio.to_thread(request_callable, url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            if attempt >= _RETRY_MAX_ATTEMPTS or (time.monotonic() - start) >= _RETRY_MAX_TOTAL_SECONDS:
                raise GoogleCalendarError("Google Calendar request failed due to network error") from exc
            delay = min(_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)), _RETRY_MAX_DELAY_SECONDS)
            delay += random.uniform(0, 0.05)
            logger.warning(
                "Transient Google Calendar network error, retrying",
                extra={"method": method_name, "attempt": attempt, "delay_s": round(delay, 3)},
            )
            await asyncio.sleep(delay)
            attempt += 1
            continue

        if 500 <= response.status_code < 600:
            if attempt >= _RETRY_MAX_ATTEMPTS or (time.monotonic() - start) >= _RETRY_MAX_TOTAL_SECONDS:
                return response
            delay = min(_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)), _RETRY_MAX_DELAY_SECONDS)
            delay += random.uniform(0, 0.05)
            logger.warning(
                "Transient Google Calendar 5xx response, retrying",
                extra={
                    "method": method_name,
                    "attempt": attempt,
                    "status_code": response.status_code,
                    "delay_s": round(delay, 3),
                },
            )
            await asyncio.sleep(delay)
            attempt += 1
            continue

        return response


async def list_calendars(specialist_id: uuid.UUID) -> list[dict[str, Any]]:
    started = time.monotonic()
    try:
        headers = await _build_headers(specialist_id)
        response = await _calendar_request_with_retry(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/users/me/calendarList",
            method_name="GET",
            headers=headers,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)
        items = response.json().get("items", [])
        log_event(
            logger,
            logging.INFO,
            event="google_api_call",
            alias="list_calendars",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="ok",
            http_status=response.status_code,
            events_count=len(items),
            specialist_id=specialist_id,
        )
        return items
    except Exception as exc:
        logger.exception(
            "google calendar call failed",
            extra={"event": "google_api_call", "alias": "list_calendars", "exception_class": exc.__class__.__name__},
        )
        await _notify_google_calendar_exception("services.google_calendar.list_calendars", exc, specialist_id)
        raise


async def get_primary_calendar_timezone(specialist_id: uuid.UUID) -> str:
    try:
        headers = await _build_headers(specialist_id)
        response = await _calendar_request_with_retry(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/users/me/calendarList/primary",
            method_name="GET",
            headers=headers,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)

        tz = (response.json().get("timeZone") or "").strip()
        if not tz:
            tz = "UTC"

        log_event(
            logger,
            logging.INFO,
            event="google_calendar.primary_timezone_fetched",
            specialist_id=specialist_id,
            tz=tz,
        )
        return tz
    except Exception as exc:
        logger.exception(
            "google calendar primary timezone fetch failed",
            extra={
                "event": "google_api_call",
                "alias": "get_primary_calendar_timezone",
                "exception_class": exc.__class__.__name__,
            },
        )
        await _notify_google_calendar_exception(
            "services.google_calendar.get_primary_calendar_timezone",
            exc,
            specialist_id,
        )
        raise


async def resolve_tz_for_calendar_creation(*, specialist_id: uuid.UUID, profile_tz: str | None) -> str:
    profile_tz_norm = (profile_tz or "").strip()
    if not profile_tz_norm or profile_tz_norm == "UTC":
        return await get_primary_calendar_timezone(specialist_id)
    return profile_tz_norm


async def get_calendar(specialist_id: uuid.UUID, calendar_id: str) -> dict[str, Any]:
    try:
        headers = await _build_headers(specialist_id)
        response = await _calendar_request_with_retry(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}",
            method_name="GET",
            headers=headers,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)
        return response.json()
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.get_calendar", exc, specialist_id)
        raise


async def create_bot_calendar(specialist_id: uuid.UUID, public_name: str, tz: str = "UTC") -> dict[str, Any]:
    started = time.monotonic()
    try:
        headers = await _build_headers(specialist_id)
        payload = {
            "summary": f"Zumbot - {public_name}",
            "description": "Calendar created by Zumbot for booking sessions",
            "timeZone": tz,
        }
        response = await _calendar_request_with_retry(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars",
            method_name="POST",
            headers=headers,
            json=payload,
        )
        if response.status_code not in (200, 201):
            _raise_calendar_error(response)
        payload = response.json()
        log_event(
            logger,
            logging.INFO,
            event="google_api_call",
            alias="create_bot_calendar",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="ok",
            http_status=response.status_code,
            events_count=1,
            specialist_id=specialist_id,
        )
        return payload
    except Exception as exc:
        logger.exception(
            "google calendar call failed",
            extra={"event": "google_api_call", "alias": "create_bot_calendar", "exception_class": exc.__class__.__name__},
        )
        await _notify_google_calendar_exception("services.google_calendar.create_bot_calendar", exc, specialist_id)
        raise


async def ensure_calendar_access(specialist_id: uuid.UUID, calendar_id: str) -> bool:
    try:
        headers = await _build_headers(specialist_id)
        response = await _calendar_request_with_retry(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/users/me/calendarList/{calendar_id}",
            method_name="GET",
            headers=headers,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)

        role = response.json().get("accessRole")
        if role not in {"owner", "writer"}:
            raise GoogleCalendarInsufficientPermissionsError(
                f"Calendar access role '{role}' is not enough to create events"
            )
        return True
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.ensure_calendar_access", exc, specialist_id)
        raise


async def create_and_cleanup_test_event(specialist_id: uuid.UUID, calendar_id: str, tz: str = "UTC") -> None:
    try:
        headers = await _build_headers(specialist_id)
        start_dt = datetime.now(timezone.utc) + timedelta(minutes=7)
        end_dt = start_dt + timedelta(minutes=5)

        payload = {
            "summary": "Zumbot test event (auto)",
            "description": "Created automatically to verify access",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
        }

        create_response = await _calendar_request_with_retry(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events",
            method_name="POST",
            headers=headers,
            json=payload,
        )
        if create_response.status_code not in (200, 201):
            _raise_calendar_error(create_response)

        event_id = create_response.json().get("id")
        if not event_id:
            raise GoogleCalendarError("Smoke-test event id is missing")

        delete_response = await _calendar_request_with_retry(
            requests.delete,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events/{event_id}",
            method_name="DELETE",
            headers=headers,
        )
        if delete_response.status_code not in (200, 204):
            _raise_calendar_error(delete_response)
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.create_and_cleanup_test_event", exc, specialist_id)
        raise


async def create_appointment_event(
    *,
    specialist_id: uuid.UUID,
    calendar_id: str,
    start_at_utc: datetime,
    end_at_utc: datetime,
    specialist_tz: str,
    client_display_name: str | None,
    client_tg_username: str | None = None,
    client_tg_user_id: int | None = None,
    client_code: str | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        headers = await _build_headers(specialist_id)
        display_name = (client_display_name or "").strip()
        base_name = display_name or "Клиент"

        normalized_username = (client_tg_username or "").strip().lstrip("@") or None
        display_username = f"@{normalized_username}" if normalized_username else None

        fallback_summary = f"Сессия с {base_name}"
        if normalized_username:
            summary = f"Сессия с {base_name} ({display_username})"
        elif client_code:
            summary = f"Сессия с {base_name} (#{client_code})"
        elif client_tg_user_id:
            summary = f"Сессия с {base_name} (tg_id={client_tg_user_id})"
        else:
            summary = fallback_summary

        description_lines = ["Создано автоматически после подтверждения записи в боте"]
        if base_name:
            description_lines.append(f"Клиент: {base_name}")
        if client_code:
            description_lines.append(f"Client code: {client_code}")
        if normalized_username:
            description_lines.append(f"Telegram: {display_username}")
            description_lines.append(f"Link: https://t.me/{normalized_username}")
        elif client_tg_user_id:
            description_lines.append(f"Telegram: tg_user_id={client_tg_user_id}")
            description_lines.append(f"Link: tg://user?id={client_tg_user_id}")
        description = "\n".join(description_lines)

        payload = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_at_utc.isoformat(), "timeZone": specialist_tz},
            "end": {"dateTime": end_at_utc.isoformat(), "timeZone": specialist_tz},
        }

        response = await _calendar_request_with_retry(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events",
            method_name="POST",
            headers=headers,
            json=payload,
        )
        if response.status_code not in (200, 201):
            _raise_calendar_error(response)
        body = response.json()
        if not body.get("id"):
            raise GoogleCalendarError("Google Calendar event id is missing")

        log_event(
            logger,
            logging.INFO,
            event="google_api_call",
            alias="create_appointment_event",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="ok",
            http_status=response.status_code,
            events_count=1,
            specialist_id=specialist_id,
        )
        return body
    except Exception as exc:
        logger.exception(
            "google calendar call failed",
            extra={"event": "google_api_call", "alias": "create_appointment_event", "exception_class": exc.__class__.__name__},
        )
        await _notify_google_calendar_exception("services.google_calendar.create_appointment_event", exc, specialist_id)
        raise


async def update_appointment_event(
    *,
    specialist_id: uuid.UUID,
    calendar_id: str,
    google_event_id: str,
    start_at_utc: datetime,
    end_at_utc: datetime,
    specialist_tz: str,
    client_display_name: str | None,
    client_tg_username: str | None = None,
    client_tg_user_id: int | None = None,
    client_code: str | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        headers = await _build_headers(specialist_id)
        display_name = (client_display_name or "").strip()
        base_name = display_name or "Клиент"

        normalized_username = (client_tg_username or "").strip().lstrip("@") or None
        display_username = f"@{normalized_username}" if normalized_username else None

        fallback_summary = f"Сессия с {base_name}"
        if normalized_username:
            summary = f"Сессия с {base_name} ({display_username})"
        elif client_code:
            summary = f"Сессия с {base_name} (#{client_code})"
        elif client_tg_user_id:
            summary = f"Сессия с {base_name} (tg_id={client_tg_user_id})"
        else:
            summary = fallback_summary

        description_lines = ["Создано автоматически после подтверждения записи в боте"]
        if base_name:
            description_lines.append(f"Клиент: {base_name}")
        if client_code:
            description_lines.append(f"Client code: {client_code}")
        if normalized_username:
            description_lines.append(f"Telegram: {display_username}")
            description_lines.append(f"Link: https://t.me/{normalized_username}")
        elif client_tg_user_id:
            description_lines.append(f"Telegram: tg_user_id={client_tg_user_id}")
            description_lines.append(f"Link: tg://user?id={client_tg_user_id}")
        description = "\n".join(description_lines)

        payload = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_at_utc.isoformat(), "timeZone": specialist_tz},
            "end": {"dateTime": end_at_utc.isoformat(), "timeZone": specialist_tz},
        }

        response = await _calendar_request_with_retry(
            requests.put,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events/{google_event_id}",
            method_name="PUT",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)
        body = response.json()
        if not body.get("id"):
            raise GoogleCalendarError("Google Calendar event id is missing")

        log_event(
            logger,
            logging.INFO,
            event="google_api_call",
            alias="update_appointment_event",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="ok",
            http_status=response.status_code,
            events_count=1,
            specialist_id=specialist_id,
        )
        return body
    except Exception as exc:
        logger.exception(
            "google calendar call failed",
            extra={"event": "google_api_call", "alias": "update_appointment_event", "exception_class": exc.__class__.__name__},
        )
        await _notify_google_calendar_exception("services.google_calendar.update_appointment_event", exc, specialist_id)
        raise


async def get_busy_intervals_for_day(
    *,
    specialist_id: uuid.UUID,
    calendar_id: str,
    specialist_tz: str,
    target_date_local_specialist: date,
) -> list[tuple[datetime, datetime]]:
    try:
        headers = await _build_headers(specialist_id)
        specialist_zone = ZoneInfo(specialist_tz)
        day_start_local = datetime.combine(target_date_local_specialist, datetime.min.time(), tzinfo=specialist_zone)
        day_end_local = day_start_local + timedelta(days=1)

        payload = {
            "timeMin": day_start_local.astimezone(timezone.utc).isoformat(),
            "timeMax": day_end_local.astimezone(timezone.utc).isoformat(),
            "items": [{"id": calendar_id}],
        }
        response = await _calendar_request_with_retry(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/freeBusy",
            method_name="POST",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)

        busy_items = response.json().get("calendars", {}).get(calendar_id, {}).get("busy", [])
        result: list[tuple[datetime, datetime]] = []
        for item in busy_items:
            busy_start_raw = item.get("start")
            busy_end_raw = item.get("end")
            if not busy_start_raw or not busy_end_raw:
                continue
            busy_start = datetime.fromisoformat(busy_start_raw.replace("Z", "+00:00")).astimezone(specialist_zone)
            busy_end = datetime.fromisoformat(busy_end_raw.replace("Z", "+00:00")).astimezone(specialist_zone)
            result.append((busy_start.replace(tzinfo=None), busy_end.replace(tzinfo=None)))

        return result
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.get_busy_intervals_for_day", exc, specialist_id)
        raise
