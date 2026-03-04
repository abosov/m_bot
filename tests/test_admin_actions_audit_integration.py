import importlib
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

pytest.importorskip("aiosqlite")


_SECRET_MARKERS = ("token", "password", "secret", "api_key", "authorization", "cookie")


def load_app(tmp_path, monkeypatch):
    db_path = tmp_path / "admin_actions_audit.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    monkeypatch.setenv("ADMIN_UI_PASSWORD", "ui-secret")

    import config
    import database
    import admin_api
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(admin_api)
    importlib.reload(web_server)
    return web_server.app, database


def login_admin_ui(client: TestClient) -> tuple[str, str]:
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")
    assert session_cookie
    assert csrf_cookie
    return session_cookie, csrf_cookie


def assert_audit_payload_has_no_secrets(payload: dict) -> None:
    payload_dump = json.dumps(payload).lower()
    assert "encrypted-token" not in payload_dump
    for marker in _SECRET_MARKERS:
        assert f'"{marker}"' not in payload_dump


@pytest.mark.asyncio
async def test_disable_normal_specialist_writes_success_audit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    normal_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=normal_id, status=database.SpecialistStatus.active))
        await session.commit()

    client = TestClient(app)
    session_cookie, csrf_cookie = login_admin_ui(client)

    response = client.post(
        f"/admin/ui/specialists/{normal_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert response.status_code == 200

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, normal_id)
        assert specialist is not None
        assert specialist.status == database.SpecialistStatus.suspended

        audit = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == normal_id,
                    database.AdminAuditLog.action == "disable_specialist",
                )
            )
        ).scalars().one()
        assert audit.success is True
        assert audit.error_code is None
        assert audit.payload_json == {"old_status": "active", "new_status": "disabled"}
        assert_audit_payload_has_no_secrets(audit.payload_json)


@pytest.mark.asyncio
async def test_disable_system_specialist_forbidden_with_failed_audit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    system_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=system_id,
                status=database.SpecialistStatus.active,
                is_system=True,
            )
        )
        await session.commit()

    client = TestClient(app)
    session_cookie, csrf_cookie = login_admin_ui(client)

    response = client.post(
        f"/admin/ui/specialists/{system_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert response.status_code == 403

    async with database.async_session_factory() as session:
        audit = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == system_id,
                    database.AdminAuditLog.action == "disable_specialist",
                )
            )
        ).scalars().one()
        assert audit.success is False
        assert audit.error_code == "FORBIDDEN_SYSTEM"
        assert_audit_payload_has_no_secrets(audit.payload_json)


@pytest.mark.asyncio
async def test_reset_oauth_deletes_row_and_audits_deleted_rows(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    normal_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=normal_id, status=database.SpecialistStatus.active))
        session.add(
            database.GoogleOAuth(
                specialist_id=normal_id,
                refresh_token_encrypted="encrypted-token",
                scopes="scope-a scope-b",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    client = TestClient(app)
    session_cookie, csrf_cookie = login_admin_ui(client)

    response = client.post(
        f"/admin/ui/specialists/{normal_id}/reset-oauth",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert response.status_code == 200
    assert response.json()["oauth_connected"] is False

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, normal_id)
        assert oauth is None

        audit = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == normal_id,
                    database.AdminAuditLog.action == "reset_oauth",
                )
            )
        ).scalars().one()
        assert audit.success is True
        assert audit.payload_json["deleted_rows"] == 1
        assert_audit_payload_has_no_secrets(audit.payload_json)


@pytest.mark.asyncio
async def test_change_tariff_valid_and_invalid_with_audit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    normal_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=normal_id, status=database.SpecialistStatus.active))
        session.add(
            database.SpecialistProfile(
                specialist_id=normal_id,
                public_name="Tariff Test",
                owner_tg_user_id=99,
                specialist_timezone="UTC",
                tariff_plan=database.TariffPlan.start,
            )
        )
        await session.commit()

    client = TestClient(app)
    session_cookie, csrf_cookie = login_admin_ui(client)

    valid_response = client.post(
        f"/admin/ui/specialists/{normal_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"tariff_plan": database.TariffPlan.pro.value},
    )
    assert valid_response.status_code == 200

    invalid_response = client.post(
        f"/admin/ui/specialists/{normal_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"tariff_plan": "enterprise"},
    )
    assert invalid_response.status_code == 422

    async with database.async_session_factory() as session:
        audits = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == normal_id,
                    database.AdminAuditLog.action == "change_tariff",
                )
            )
        ).scalars().all()

        assert len(audits) == 2

        success_audit = next(row for row in audits if row.success is True)
        failed_audit = next(row for row in audits if row.success is False)

        assert success_audit.payload_json == {"old_tariff": "start", "new_tariff": "pro"}
        assert failed_audit.error_code == "VALIDATION"
        assert failed_audit.payload_json == {"old_tariff": "pro", "new_tariff": "enterprise"}

        for row in audits:
            assert_audit_payload_has_no_secrets(row.payload_json)
