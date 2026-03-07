from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.test_admin_api import load_app


async def _run_us_ad_13_reset_flow(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        client_row = database.Client(
            specialist_id=specialist_id,
            tg_user_id=501,
            client_code="USAD13-001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=True,
                is_system=False,
            )
        )
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="US-AD-13 Specialist",
                owner_tg_user_id=9501,
                owner_tg_username="us_ad_13_owner",
                specialist_timezone="UTC",
            )
        )
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted="enc",
                scopes="calendar",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=now,
            )
        )
        session.add(
            database.SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id="us-ad-13-cal",
                calendar_summary="US-AD-13",
                calendar_time_zone="UTC",
                source=database.SpecialistCalendarSource.selected,
            )
        )

        session.add(client_row)
        await session.flush()

        session.add(
            database.Appointment(
                specialist_id=specialist_id,
                client_id=client_row.client_id,
                start_at_utc=now,
                end_at_utc=now + timedelta(minutes=30),
                booking_state=database.BookingState.pending,
                idempotency_key="us-ad-13-reset",
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    preflight_response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-test-data",
        json={"step": "preflight"},
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert preflight_response.status_code == 200
    preflight_payload = preflight_response.json()

    confirm_response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-test-data",
        json={
            "step": "confirm",
            "confirmation_token": preflight_payload["confirmation_token"],
            "confirmation_phrase": preflight_payload["confirmation_phrase"],
        },
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert confirm_response.status_code == 200

    execute_response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-test-data",
        json={
            "step": "execute",
            "confirmation_token": preflight_payload["confirmation_token"],
            "confirmation_phrase": preflight_payload["confirmation_phrase"],
        },
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert execute_response.status_code == 200

    async with database.async_session_factory() as session:
        appointments_count = await session.scalar(
            select(func.count()).select_from(database.Appointment).where(database.Appointment.specialist_id == specialist_id)
        )
        clients_count = await session.scalar(
            select(func.count()).select_from(database.Client).where(database.Client.specialist_id == specialist_id)
        )
        specialist_exists = await session.scalar(
            select(database.Specialist.specialist_id).where(database.Specialist.specialist_id == specialist_id)
        )
        oauth_exists = await session.scalar(
            select(database.GoogleOAuth.specialist_id).where(database.GoogleOAuth.specialist_id == specialist_id)
        )
        calendar_exists = await session.scalar(
            select(database.SpecialistCalendarSettings.specialist_id).where(
                database.SpecialistCalendarSettings.specialist_id == specialist_id
            )
        )

    return {
        "execute_payload": execute_response.json(),
        "appointments_count": int(appointments_count or 0),
        "clients_count": int(clients_count or 0),
        "specialist_exists": specialist_exists,
        "oauth_exists": oauth_exists,
        "calendar_exists": calendar_exists,
        "specialist_id": specialist_id,
    }


@pytest.mark.asyncio
async def test_us_ad_13_reset_deletes_runtime_data(tmp_path, monkeypatch):
    outcome = await _run_us_ad_13_reset_flow(tmp_path, monkeypatch)

    assert outcome["appointments_count"] == 0
    assert outcome["clients_count"] == 0
    assert outcome["execute_payload"]["deleted_counts"]["appointments"] == 1
    assert outcome["execute_payload"]["deleted_counts"]["clients"] == 1


@pytest.mark.asyncio
async def test_us_ad_13_identity_preserved(tmp_path, monkeypatch):
    outcome = await _run_us_ad_13_reset_flow(tmp_path, monkeypatch)

    assert outcome["specialist_exists"] == outcome["specialist_id"]


@pytest.mark.asyncio
async def test_us_ad_13_oauth_preserved(tmp_path, monkeypatch):
    outcome = await _run_us_ad_13_reset_flow(tmp_path, monkeypatch)

    assert outcome["oauth_exists"] == outcome["specialist_id"]


@pytest.mark.asyncio
async def test_us_ad_13_calendar_preserved(tmp_path, monkeypatch):
    outcome = await _run_us_ad_13_reset_flow(tmp_path, monkeypatch)

    assert outcome["calendar_exists"] == outcome["specialist_id"]
