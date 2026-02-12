import logging
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlalchemy import select

import config
from database import GoogleOAuth, async_session_factory
from services.crypto import decrypt_token
from services.alerting import notify_exception

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3"

logger = logging.getLogger(__name__)


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


async def list_calendars(specialist_id: uuid.UUID) -> list[dict[str, Any]]:
    try:
        headers = await _build_headers(specialist_id)
        response = await asyncio.to_thread(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/users/me/calendarList",
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)
        return response.json().get("items", [])
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.list_calendars", exc, specialist_id)
        raise


async def get_calendar(specialist_id: uuid.UUID, calendar_id: str) -> dict[str, Any]:
    try:
        headers = await _build_headers(specialist_id)
        response = await asyncio.to_thread(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}",
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            _raise_calendar_error(response)
        return response.json()
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.get_calendar", exc, specialist_id)
        raise


async def create_bot_calendar(specialist_id: uuid.UUID, public_name: str, tz: str = "UTC") -> dict[str, Any]:
    try:
        headers = await _build_headers(specialist_id)
        payload = {
            "summary": f"Zumbot - {public_name}",
            "description": "Calendar created by Zumbot for booking sessions",
            "timeZone": tz,
        }
        response = await asyncio.to_thread(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if response.status_code not in (200, 201):
            _raise_calendar_error(response)
        return response.json()
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.create_bot_calendar", exc, specialist_id)
        raise


async def ensure_calendar_access(specialist_id: uuid.UUID, calendar_id: str) -> bool:
    try:
        headers = await _build_headers(specialist_id)
        response = await asyncio.to_thread(
            requests.get,
            f"{GOOGLE_CALENDAR_BASE_URL}/users/me/calendarList/{calendar_id}",
            headers=headers,
            timeout=10,
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

        create_response = await asyncio.to_thread(
            requests.post,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if create_response.status_code not in (200, 201):
            _raise_calendar_error(create_response)

        event_id = create_response.json().get("id")
        if not event_id:
            raise GoogleCalendarError("Smoke-test event id is missing")

        delete_response = await asyncio.to_thread(
            requests.delete,
            f"{GOOGLE_CALENDAR_BASE_URL}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
            timeout=10,
        )
        if delete_response.status_code not in (200, 204):
            _raise_calendar_error(delete_response)
    except Exception as exc:
        await _notify_google_calendar_exception("services.google_calendar.create_and_cleanup_test_event", exc, specialist_id)
        raise
