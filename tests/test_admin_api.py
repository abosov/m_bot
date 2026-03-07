import base64
import importlib
import json
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

pytest.importorskip("aiosqlite")


def load_app(tmp_path, monkeypatch, admin_key: str | None, admin_ui_password: str | None = None):
    db_path = tmp_path / "admin_api.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    if admin_key:
        monkeypatch.setenv("ADMIN_API_KEY", admin_key)
    else:
        monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    if admin_ui_password:
        monkeypatch.setenv("ADMIN_UI_PASSWORD", admin_ui_password)
    else:
        monkeypatch.delenv("ADMIN_UI_PASSWORD", raising=False)

    import config
    import database
    import admin_api
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(admin_api)
    importlib.reload(web_server)
    return web_server.app, database


@pytest.mark.asyncio
async def test_admin_logs_requires_key(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None)
    client = TestClient(app)
    response = client.get("/admin/logs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_login_page_returns_404_when_admin_ui_disabled(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None)
    client = TestClient(app)

    response = client.get("/admin/login")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_login_page_returns_200_html_when_admin_ui_enabled(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/login")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<h1>Zumbot Admin Login</h1>" in response.text


@pytest.mark.asyncio
async def test_admin_login_returns_404_for_wrong_password(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.post("/admin/login", data={"password": "wrong"}, follow_redirects=False)

    assert response.status_code == 404






@pytest.mark.asyncio
async def test_admin_login_rotates_session_old_cookie_invalid(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    login_response_1 = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    old_cookie = login_response_1.cookies.get("admin_session")

    login_response_2 = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    new_cookie = login_response_2.cookies.get("admin_session")

    assert old_cookie
    assert new_cookie
    assert old_cookie != new_cookie

    old_response = client.get("/admin", cookies={"admin_session": old_cookie})
    new_response = client.get("/admin", cookies={"admin_session": new_cookie})

    assert old_response.status_code == 404
    assert new_response.status_code == 200


@pytest.mark.asyncio
async def test_admin_session_cookie_contains_issued_at(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    assert session_cookie

    payload_b64 = session_cookie.split(".", 1)[0]
    payload_padding = "=" * (-len(payload_b64) % 4)
    payload_raw = base64.urlsafe_b64decode(f"{payload_b64}{payload_padding}").decode("utf-8")
    payload = json.loads(payload_raw)

    assert "issued_at" in payload
    assert isinstance(payload["issued_at"], int)

@pytest.mark.asyncio
async def test_admin_login_logs_success_with_ip_and_request_id(tmp_path, monkeypatch, caplog):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    with caplog.at_level("INFO"):
        response = client.post(
            "/admin/login",
            data={"password": "ui-secret"},
            follow_redirects=False,
            headers={"X-Request-ID": "req-login-ok"},
        )

    assert response.status_code == 303
    assert "event=admin_login_success" in caplog.text
    assert "request_id=req-login-ok" in caplog.text
    assert "ip=testclient" in caplog.text
    assert "timestamp=" in caplog.text
    assert "ui-secret" not in caplog.text


@pytest.mark.asyncio
async def test_admin_login_logs_failed_with_ip_and_request_id(tmp_path, monkeypatch, caplog):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    with caplog.at_level("INFO"):
        response = client.post(
            "/admin/login",
            data={"password": "wrong-password"},
            follow_redirects=False,
            headers={"X-Request-ID": "req-login-fail"},
        )

    assert response.status_code == 404
    assert "event=admin_login_failed" in caplog.text
    assert "reason=invalid_password" in caplog.text
    assert "request_id=req-login-fail" in caplog.text
    assert "ip=testclient" in caplog.text
    assert "timestamp=" in caplog.text
    assert "wrong-password" not in caplog.text

@pytest.mark.asyncio
async def test_admin_login_sets_cookie_for_correct_password(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    set_cookie = response.headers["set-cookie"]
    assert "admin_session=" in set_cookie
    assert "admin_csrf=" in set_cookie
    assert "Max-Age=43200" in set_cookie
    assert "expires=" in set_cookie.lower()
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie

    set_cookie_headers = response.headers.get_list("set-cookie")
    session_cookie_header = next(v for v in set_cookie_headers if v.startswith("admin_session="))
    csrf_cookie_header = next(v for v in set_cookie_headers if v.startswith("admin_csrf="))
    assert "HttpOnly" in session_cookie_header
    assert "Secure" in session_cookie_header
    assert "SameSite=lax" in session_cookie_header
    assert "Secure" in csrf_cookie_header
    assert "SameSite=lax" in csrf_cookie_header






@pytest.mark.asyncio
async def test_admin_logout_clears_cookies(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    assert session_cookie
    assert csrf_cookie

    response = client.post(
        "/admin/logout",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    set_cookie = response.headers.get("set-cookie", "")
    assert "admin_session=" in set_cookie
    assert "admin_csrf=" in set_cookie
    assert "Max-Age=0" in set_cookie

    admin_page_response = client.get("/admin")
    assert admin_page_response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_post_requires_csrf_header(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    @app.post("/admin/ui/test-csrf")
    async def _test_csrf_endpoint():
        return {"ok": True}

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    assert csrf_cookie

    missing_csrf = client.post(
        "/admin/ui/test-csrf",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
    )
    assert missing_csrf.status_code == 403

    valid_csrf = client.post(
        "/admin/ui/test-csrf",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert valid_csrf.status_code == 200
    assert valid_csrf.json() == {"ok": True}


@pytest.mark.asyncio
async def test_admin_ui_post_unauth_remains_404_even_with_csrf_header(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    @app.post("/admin/ui/test-csrf-unauth")
    async def _test_csrf_endpoint_unauth():
        return {"ok": True}

    client = TestClient(app)

    response = client.post(
        "/admin/ui/test-csrf-unauth",
        cookies={"admin_csrf": "anything"},
        headers={"X-CSRF-Token": "anything"},
    )

    assert response.status_code == 404



@pytest.mark.asyncio
async def test_admin_ui_disable_specialist_happy_path(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "specialist_id": str(specialist_id), "status": "disabled"}

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.status == database.SpecialistStatus.suspended

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "disable_specialist",
                )
            )
        ).scalars().one()
        assert audit_row.success is True
        assert audit_row.payload_json == {"old_status": "active", "new_status": "disabled"}


@pytest.mark.asyncio
async def test_admin_ui_disable_specialist_idempotent_second_call(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.suspended, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    first = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    second = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "disabled"

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.status == database.SpecialistStatus.suspended


@pytest.mark.asyncio
async def test_admin_ui_disable_specialist_forbidden_for_non_test_account(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=False))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403

    async with database.async_session_factory() as session:
        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "disable_specialist",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "FORBIDDEN_NOT_TEST"


@pytest.mark.asyncio
async def test_admin_ui_disable_specialist_forbidden_for_system_account(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_system=True,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.status == database.SpecialistStatus.active

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "disable_specialist",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "FORBIDDEN_SYSTEM"


@pytest.mark.asyncio
async def test_admin_ui_disable_specialist_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/disable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
    )

    assert response.status_code == 403




@pytest.mark.asyncio
async def test_admin_ui_enable_specialist_after_disable(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.suspended, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/enable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "specialist_id": str(specialist_id), "status": "active"}

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.status == database.SpecialistStatus.active

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "enable_specialist",
                )
            )
        ).scalars().one()
        assert audit_row.success is True
        assert audit_row.payload_json == {"old_status": "suspended", "new_status": "active"}


@pytest.mark.asyncio
async def test_admin_ui_enable_specialist_idempotent(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    first = client.post(
        f"/admin/ui/specialists/{specialist_id}/enable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    second = client.post(
        f"/admin/ui/specialists/{specialist_id}/enable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"ok": True, "specialist_id": str(specialist_id), "status": "active"}


@pytest.mark.asyncio
async def test_admin_ui_enable_specialist_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.suspended, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/enable",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
    )

    assert response.status_code == 403




@pytest.mark.asyncio
async def test_admin_ui_reset_oauth_removes_google_oauth_and_detail_shows_disconnected(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted="encrypted-token",
                scopes="scope-a scope-b",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            database.SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id="primary-calendar",
                source=database.SpecialistCalendarSource.selected,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-oauth",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "specialist_id": str(specialist_id), "oauth_connected": False}

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is None

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "reset_oauth",
                )
            )
        ).scalars().one()
        assert audit_row.success is True
        assert audit_row.payload_json["deleted_rows"] == 1

    detail_response = client.get(
        f"/admin/ui/specialists/{specialist_id}",
        cookies={"admin_session": session_cookie},
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["integration"]["oauth_connected"] is False
    # Calendar setting is intentionally kept in MVP after OAuth reset.
    assert detail_payload["integration"]["calendar_selected"] is True


@pytest.mark.asyncio
async def test_admin_ui_reset_oauth_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-oauth",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_ui_reset_oauth_forbidden_for_non_test_specialist(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=False))
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted="encrypted-token",
                scopes="scope-a",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-oauth",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403

    async with database.async_session_factory() as session:
        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "reset_oauth",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "FORBIDDEN_NOT_TEST"


@pytest.mark.asyncio
async def test_admin_ui_reset_oauth_forbidden_for_system_specialist(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_system=True,
            )
        )
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted="encrypted-token",
                scopes="scope-a",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/reset-oauth",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403

    async with database.async_session_factory() as session:
        oauth = await session.get(database.GoogleOAuth, specialist_id)
        assert oauth is not None

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "reset_oauth",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "FORBIDDEN_SYSTEM"




@pytest.mark.asyncio
async def test_admin_ui_change_tariff_valid_plan(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Tariff Specialist",
                owner_tg_user_id=12345,
                specialist_timezone="UTC",
                tariff_plan=database.TariffPlan.start,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"tariff_plan": database.TariffPlan.pro.value},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "specialist_id": str(specialist_id),
        "tariff_plan": database.TariffPlan.pro.value,
    }

    async with database.async_session_factory() as session:
        profile = await session.get(database.SpecialistProfile, specialist_id)
        assert profile is not None
        assert profile.tariff_plan == database.TariffPlan.pro

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "change_tariff",
                )
            )
        ).scalars().one()
        assert audit_row.success is True
        assert audit_row.payload_json == {"old_tariff": "start", "new_tariff": "pro"}


@pytest.mark.asyncio
async def test_admin_ui_change_tariff_invalid_plan_returns_422_and_audits_validation(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Tariff Specialist",
                owner_tg_user_id=12345,
                specialist_timezone="UTC",
                tariff_plan=database.TariffPlan.start,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"tariff_plan": "enterprise"},
    )

    assert response.status_code == 422

    async with database.async_session_factory() as session:
        profile = await session.get(database.SpecialistProfile, specialist_id)
        assert profile is not None
        assert profile.tariff_plan == database.TariffPlan.start

        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "change_tariff",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "VALIDATION"


@pytest.mark.asyncio
async def test_admin_ui_change_tariff_forbidden_for_non_test_specialist(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=False))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Tariff Specialist",
                owner_tg_user_id=12345,
                specialist_timezone="UTC",
                tariff_plan=database.TariffPlan.start,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"tariff_plan": database.TariffPlan.pro.value},
    )

    assert response.status_code == 403

    async with database.async_session_factory() as session:
        audit_row = (
            await session.execute(
                select(database.AdminAuditLog).where(
                    database.AdminAuditLog.target_id == specialist_id,
                    database.AdminAuditLog.action == "change_tariff",
                )
            )
        ).scalars().one()
        assert audit_row.success is False
        assert audit_row.error_code == "FORBIDDEN_NOT_TEST"


@pytest.mark.asyncio
async def test_admin_ui_change_tariff_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Tariff Specialist",
                owner_tg_user_id=12345,
                specialist_timezone="UTC",
                tariff_plan=database.TariffPlan.start,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/tariff",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        json={"tariff_plan": database.TariffPlan.pro.value},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_page_returns_200_with_valid_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_VERSION", "build-123")
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<h1>Zumbot Admin Console</h1>" in response.text
    assert "Environment: local" in response.text
    assert "Server time (UTC):" in response.text
    assert "Version: build-123" in response.text
    assert "id='admin-overview'" in response.text
    assert "Loading overview…" in response.text
    assert "const url='/admin/ui/overview?'+params.toString();" in response.text
    assert "id='specialists-table'" in response.text
    assert "<th>Flags</th>" in response.text
    assert "badge-test" in response.text
    assert "badge-system" in response.text
    assert "row-test" in response.text
    assert "<a href='#logs'>Logs</a>" in response.text
    assert "<a href='#heartbeats'>Heartbeats</a>" in response.text
    assert "<a href='#audit-log'>Audit Log</a>" in response.text
    assert "id='logout-btn'" in response.text
    assert "await fetch('/admin/logout', { method:'POST' });" in response.text
    assert "id='audit-log-section'" in response.text
    assert "id='audit-limit'" in response.text
    assert "id='audit-prev'" in response.text
    assert "id='audit-next'" in response.text
    assert "No audit records" in response.text
    assert "fetch('/admin/ui/logs?'+params.toString(),{credentials:'same-origin'})" in response.text
    assert "fetch('/admin/ui/heartbeats?'+params.toString(),{credentials:'same-origin'})" in response.text
    assert "fetch('/admin/ui/audit-log?'+params.toString(),{credentials:'same-origin'})" in response.text
    assert "id='oauth-missing-filter'" in response.text
    assert "id='calendar-missing-filter'" in response.text
    assert "id='inactive-days-filter'" in response.text
    assert "id='test-only-filter'" in response.text
    assert "params.set('oauth_missing','1')" in response.text
    assert "params.set('calendar_missing','1')" in response.text
    assert "params.set('test_only','1')" in response.text
    assert "params.set('inactive_days_gt',inactiveDaysRaw)" in response.text


@pytest.mark.asyncio
async def test_admin_ui_specialists_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/specialists")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_specialists_returns_items_with_valid_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_id,
                    public_name="UI Specialist",
                    owner_tg_user_id=3333,
                    owner_tg_username="ui_spec",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_id, tg_user_id=3333),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/specialists", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["public_name"] == "UI Specialist"
    assert payload["items"][0]["email"] is None
    assert payload["items"][0]["is_system"] is False
    assert payload["items"][0]["is_test"] is False




@pytest.mark.asyncio
async def test_admin_specialist_detail_page_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get(f"/admin/specialists/{uuid.uuid4()}", headers={"accept": "text/html"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_specialist_detail_page_renders_html_with_valid_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(f"/admin/specialists/{specialist_id}", cookies={"admin_session": session_cookie}, headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "← Back to specialists" in response.text
    assert "Loading specialist…" in response.text
    assert "Failed to load" in response.text
    assert f"const specialistId='{specialist_id}'" in response.text
    assert f"fetch('/admin/ui/specialists/'+specialistId,{{credentials:'same-origin'}})" in response.text
    assert "<h2>Basic</h2>" in response.text
    assert "<h2>Integration</h2>" in response.text
    assert "<h2>Activity</h2>" in response.text
    assert "<h2>Errors</h2>" in response.text
    assert "<h2>Admin Actions</h2>" in response.text
    assert ">Disable<" in response.text
    assert ">Enable<" in response.text
    assert ">Reset OAuth<" in response.text
    assert "Tariff" in response.text
    assert "getCookie('admin_csrf')" in response.text
    assert "'/admin/ui/specialists/'+specialistId+'/disable'" in response.text
    assert "'/admin/ui/specialists/'+specialistId+'/enable'" in response.text
    assert "'/admin/ui/specialists/'+specialistId+'/reset-oauth'" in response.text
    assert "'/admin/ui/specialists/'+specialistId+'/tariff'" in response.text




async def _seed_specialist_detail_fixture(database):
    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_id,
                    status=database.SpecialistStatus.active,
                    created_at=now,
                    is_system=False,
                    onboarding_master_completed_at=now,
                    onboarding_personal_completed_at=now,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_id,
                    public_name="Specialist A",
                    owner_tg_user_id=7010,
                    owner_tg_username="owner_a",
                    specialist_timezone="Europe/Berlin",
                    slot_step_min=20,
                    max_sessions_per_day=6,
                    tariff_plan=database.TariffPlan.pro,
                ),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_id,
                    tg_user_id=7010,
                    tg_username="spec_a",
                    tg_first_name="Anna",
                ),
                database.GoogleOAuth(
                    specialist_id=specialist_id,
                    refresh_token_encrypted="encrypted-refresh-token",
                    scopes="scope",
                    status=database.GoogleOAuthStatus.connected,
                    token_updated_at=now,
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_id,
                    calendar_id="primary",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.Client(
                    specialist_id=specialist_id,
                    tg_user_id=8101,
                    tg_username="client_one",
                    display_name="Client One",
                    client_code="CA001",
                    client_timezone="Europe/Berlin",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_id,
                    tg_user_id=8102,
                    tg_username="client_two",
                    display_name="Client Two",
                    client_code="CA002",
                    client_timezone="Europe/Berlin",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=7010,
                    direction=database.LogDirection.IN,
                    message_type="text",
                    content="message body one",
                    handler_name="handler_one",
                    created_at=now - timedelta(hours=2),
                ),
                database.MessageLog(
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=7010,
                    direction=database.LogDirection.OUT,
                    message_type="text",
                    content="message body two",
                    handler_name="handler_two",
                    created_at=now - timedelta(hours=1),
                    is_error=True,
                    error_details="sample error",
                ),
            ]
        )
        await session.commit()

    return specialist_id


@pytest.mark.asyncio
async def test_specialist_detail_ui_endpoint_security_payload(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = await _seed_specialist_detail_fixture(database)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(f"/admin/ui/specialists/{specialist_id}", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()

    assert "basic" in payload
    assert "integration" in payload
    assert "activity" in payload
    assert payload["activity"]["clients_count"] == 2
    assert len(payload["activity"]["recent_events"]) >= 2

    response_text = response.text
    assert "refresh_token" not in response_text
    assert "access_token" not in response_text
    assert "message body one" not in response_text
    assert "message body two" not in response_text
    assert "client_email" not in response_text
    assert "client_phone" not in response_text


@pytest.mark.asyncio
async def test_specialist_detail_ui_endpoint_without_cookie_returns_404(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = await _seed_specialist_detail_fixture(database)

    client = TestClient(app)
    response = client.get(f"/admin/ui/specialists/{specialist_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_specialist_detail_unknown_specialist_returns_404(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(f"/admin/ui/specialists/{uuid.uuid4()}", cookies={"admin_session": session_cookie})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_specialist_detail_api_key_endpoint_auth(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = await _seed_specialist_detail_fixture(database)

    client = TestClient(app)

    ok_response = client.get(f"/admin/specialists/{specialist_id}", headers={"X-API-Key": "secret"})
    wrong_response = client.get(f"/admin/specialists/{specialist_id}", headers={"X-API-Key": "wrong"})

    assert ok_response.status_code == 200
    assert wrong_response.status_code == 403

@pytest.mark.asyncio
async def test_admin_ui_specialist_detail_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get(f"/admin/ui/specialists/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_specialist_detail_returns_404_for_missing_specialist(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(f"/admin/ui/specialists/{uuid.uuid4()}", cookies={"admin_session": session_cookie})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_specialist_detail_returns_payload_and_safe_fields(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    now = datetime(2024, 1, 10, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_id,
                    status=database.SpecialistStatus.active,
                    created_at=now,
                    onboarding_master_completed_at=now,
                    onboarding_personal_completed_at=now,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_id,
                    public_name="Detail Spec",
                    owner_tg_user_id=4444,
                    owner_tg_username="detail_owner",
                    specialist_timezone="Europe/Berlin",
                    slot_step_min=20,
                    max_sessions_per_day=5,
                    tariff_plan=database.TariffPlan.pro,
                ),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_id,
                    tg_user_id=4444,
                    tg_username="detail_spec",
                    tg_first_name="Dina",
                ),
                database.GoogleOAuth(
                    specialist_id=specialist_id,
                    refresh_token_encrypted="encrypted",
                    scopes="scope",
                    status=database.GoogleOAuthStatus.connected,
                    token_updated_at=now,
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_id,
                    calendar_id="primary",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.Client(
                    specialist_id=specialist_id,
                    tg_user_id=5555,
                    tg_username="client1",
                    display_name="Client",
                    client_code="C001",
                    client_timezone="Europe/Berlin",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=4444,
                    direction=database.LogDirection.IN,
                    message_type="text",
                    content="private message body",
                    handler_name="handler",
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        f"/admin/ui/specialists/{specialist_id}",
        cookies={"admin_session": session_cookie},
        headers={"X-Request-ID": "req-123"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["basic"]["specialist_id"] == str(specialist_id)
    assert payload["basic"]["public_name"] == "Detail Spec"
    assert payload["basic"]["status"] == "active"
    assert payload["basic"]["is_system"] is False
    assert payload["basic"]["telegram_username"] == "detail_spec"
    assert payload["basic"]["telegram_first_name"] == "Dina"

    assert payload["integration"]["oauth_connected"] is True
    assert payload["integration"]["calendar_selected"] is True
    assert payload["integration"]["selected_calendar_id"] == "primary"
    assert payload["integration"]["timezone"] == "Europe/Berlin"
    assert payload["integration"]["slot_step"] == 20
    assert payload["integration"]["max_sessions_per_day"] == 5
    assert payload["integration"]["onboarding_master_done"] is True
    assert payload["integration"]["onboarding_personal_done"] is True

    assert payload["activity"]["clients_count"] == 1
    assert payload["activity"]["last_activity_at"] is not None
    assert payload["activity"]["active_7d"] is False
    assert payload["activity"]["recent_events"]
    assert payload["activity"]["recent_events"][0]["event_type"] == "IN:text"

    assert payload["errors"] == []

    response_text = response.text
    assert "refresh_token_encrypted" not in response_text
    assert "private message body" not in response_text


@pytest.mark.asyncio
async def test_admin_ui_specialist_detail_logs_access_event(tmp_path, monkeypatch, caplog):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    with caplog.at_level("INFO"):
        response = client.get(
            f"/admin/ui/specialists/{specialist_id}",
            cookies={"admin_session": session_cookie},
            headers={"X-Request-ID": "req-log-1"},
        )

    assert response.status_code == 200
    assert "event=admin_ui_specialist_detail_access request_id=req-log-1" in caplog.text
    assert str(specialist_id) in caplog.text


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_preflight_delete_returns_aggregate_counts(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    test_specialist_a = uuid.uuid4()
    test_specialist_b = uuid.uuid4()
    non_test_specialist = uuid.uuid4()
    system_specialist = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=test_specialist_a,
                    status=database.SpecialistStatus.active,
                    is_test=True,
                    is_system=False,
                ),
                database.Specialist(
                    specialist_id=test_specialist_b,
                    status=database.SpecialistStatus.active,
                    is_test=True,
                    is_system=False,
                ),
                database.Specialist(
                    specialist_id=non_test_specialist,
                    status=database.SpecialistStatus.active,
                    is_test=False,
                    is_system=False,
                ),
                database.Specialist(
                    specialist_id=system_specialist,
                    status=database.SpecialistStatus.active,
                    is_test=False,
                    is_system=True,
                ),
            ]
        )

        test_client_1 = database.Client(
            specialist_id=test_specialist_a,
            tg_user_id=4101,
            client_code="TC001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        test_client_2 = database.Client(
            specialist_id=test_specialist_b,
            tg_user_id=4102,
            client_code="TC002",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        non_test_client = database.Client(
            specialist_id=non_test_specialist,
            tg_user_id=5101,
            client_code="NC001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )

        session.add_all([test_client_1, test_client_2, non_test_client])
        await session.flush()

        session.add_all(
            [
                database.Appointment(
                    specialist_id=test_specialist_a,
                    client_id=test_client_1.client_id,
                    start_at_utc=now,
                    end_at_utc=now + timedelta(minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="bulk-pref-test-1",
                ),
                database.Appointment(
                    specialist_id=test_specialist_b,
                    client_id=test_client_2.client_id,
                    start_at_utc=now + timedelta(hours=1),
                    end_at_utc=now + timedelta(hours=1, minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="bulk-pref-test-2",
                ),
                database.Appointment(
                    specialist_id=non_test_specialist,
                    client_id=non_test_client.client_id,
                    start_at_utc=now + timedelta(hours=2),
                    end_at_utc=now + timedelta(hours=2, minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="bulk-pref-non-test",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/test-accounts/preflight-delete",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    assert response.json() == {
        "test_specialists": 2,
        "clients": 2,
        "appointments": 2,
    }


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_preflight_delete_requires_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    response = client.get("/admin/ui/test-accounts/preflight-delete")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_preflight_delete_rejects_html_accept(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/test-accounts/preflight-delete",
        cookies={"admin_session": session_cookie},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_delete_all_creates_pending_job(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        "/admin/ui/test-accounts/delete-all",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"confirmation_phrase": "DELETE ALL TEST ACCOUNTS"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    uuid.UUID(payload["job_id"])

    async with database.async_session_factory() as session:
        job = await session.get(database.AdminBulkCleanupJob, uuid.UUID(payload["job_id"]))

    assert job is not None
    assert job.status == "pending"
    assert int(job.total_specialists) == 0
    assert int(job.processed_specialists) == 0
    assert int(job.error_count) == 0


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_delete_all_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        "/admin/ui/test-accounts/delete-all",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        json={"confirmation_phrase": "DELETE ALL TEST ACCOUNTS"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed"}


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_delete_all_requires_confirmation_phrase(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        "/admin/ui/test-accounts/delete-all",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
        json={"confirmation_phrase": "DELETE EVERYTHING"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "INVALID_CONFIRMATION_PHRASE"}


@pytest.mark.asyncio
async def test_admin_ui_test_accounts_delete_all_requires_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    response = client.post(
        "/admin/ui/test-accounts/delete-all",
        json={"confirmation_phrase": "DELETE ALL TEST ACCOUNTS"},
        headers={"X-CSRF-Token": "any"},
        cookies={"admin_csrf": "any"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_preflight_returns_counts(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        client_a = database.Client(
            specialist_id=specialist_id,
            tg_user_id=111,
            client_code="C001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        client_b = database.Client(
            specialist_id=specialist_id,
            tg_user_id=112,
            client_code="C002",
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
            database.SpecialistPublicProfile(
                id=profile_id,
                specialist_id=specialist_id,
                public_slug="spec-a",
                display_name="Spec A",
                specialization="Psychology",
                client_bot_username="spec_a_bot",
                is_published=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add_all([client_a, client_b])
        await session.flush()

        session.add_all(
            [
                database.Appointment(
                    specialist_id=specialist_id,
                    client_id=client_a.client_id,
                    start_at_utc=now,
                    end_at_utc=now + timedelta(minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="pref-appt-1",
                ),
                database.Appointment(
                    specialist_id=specialist_id,
                    client_id=client_b.client_id,
                    start_at_utc=now + timedelta(hours=1),
                    end_at_utc=now + timedelta(hours=1, minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="pref-appt-2",
                ),
            ]
        )
        session.add_all(
            [
                database.SpecialistPublicMedia(
                    profile_id=profile_id,
                    media_type="image",
                    file_key="media/1.jpg",
                    sort_order=1,
                    created_at=now,
                ),
                database.SpecialistPublicMedia(
                    profile_id=profile_id,
                    media_type="image",
                    file_key="media/2.jpg",
                    sort_order=2,
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        f"/admin/ui/specialists/{specialist_id}/delete-test/preflight",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["specialist_id"] == str(specialist_id)
    assert payload["eligible"] is True
    assert payload["counts"] == {"clients": 2, "appointments": 2, "media": 2}


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_preflight_forbidden_not_test(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=False,
                is_system=False,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        f"/admin/ui/specialists/{specialist_id}/delete-test/preflight",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_NOT_TEST"}


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_preflight_forbidden_system(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=False,
                is_system=True,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        f"/admin/ui/specialists/{specialist_id}/delete-test/preflight",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_SYSTEM"}


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_preflight_requires_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    response = client.get(f"/admin/ui/specialists/{specialist_id}/delete-test/preflight")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_deletes_entities_and_schedules_cleanup(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        client_a = database.Client(
            specialist_id=specialist_id,
            tg_user_id=301,
            client_code="D001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        client_b = database.Client(
            specialist_id=specialist_id,
            tg_user_id=302,
            client_code="D002",
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
            database.SpecialistPublicProfile(
                id=profile_id,
                specialist_id=specialist_id,
                public_slug="delete-spec",
                display_name="Delete Spec",
                specialization="Psychology",
                client_bot_username="delete_spec_bot",
                is_published=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            database.GoogleOAuth(
                specialist_id=specialist_id,
                refresh_token_encrypted="encrypted",
                scopes="scope",
                status=database.GoogleOAuthStatus.connected,
                token_updated_at=now,
            )
        )
        session.add_all([client_a, client_b])
        await session.flush()

        session.add_all(
            [
                database.Appointment(
                    specialist_id=specialist_id,
                    client_id=client_a.client_id,
                    start_at_utc=now,
                    end_at_utc=now + timedelta(minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="delete-appt-1",
                ),
                database.Appointment(
                    specialist_id=specialist_id,
                    client_id=client_b.client_id,
                    start_at_utc=now + timedelta(hours=1),
                    end_at_utc=now + timedelta(hours=1, minutes=30),
                    booking_state=database.BookingState.pending,
                    idempotency_key="delete-appt-2",
                ),
            ]
        )
        session.add_all(
            [
                database.SpecialistPublicMedia(
                    profile_id=profile_id,
                    media_type="image",
                    file_key="delete/1.jpg",
                    sort_order=1,
                    created_at=now,
                ),
                database.SpecialistPublicMedia(
                    profile_id=profile_id,
                    media_type="image",
                    file_key="delete/2.jpg",
                    sort_order=2,
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "deleted",
        "deleted_counts": {
            "appointments": 2,
            "clients": 2,
            "media": 2,
            "oauth_tokens": 1,
            "specialist": 1,
        },
    }

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        appointments_count = (
            await session.execute(select(func.count()).select_from(database.Appointment).where(database.Appointment.specialist_id == specialist_id))
        ).scalar_one()
        clients_count = (
            await session.execute(select(func.count()).select_from(database.Client).where(database.Client.specialist_id == specialist_id))
        ).scalar_one()
        media_count = (
            await session.execute(
                select(func.count())
                .select_from(database.SpecialistPublicMedia)
                .join(database.SpecialistPublicProfile, database.SpecialistPublicMedia.profile_id == database.SpecialistPublicProfile.id)
                .where(database.SpecialistPublicProfile.specialist_id == specialist_id)
            )
        ).scalar_one()
        oauth_count = (
            await session.execute(select(func.count()).select_from(database.GoogleOAuth).where(database.GoogleOAuth.specialist_id == specialist_id))
        ).scalar_one()

    assert specialist is None
    assert appointments_count == 0
    assert clients_count == 0
    assert media_count == 0
    assert oauth_count == 0


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_forbidden_not_test(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=False,
                is_system=False,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_NOT_TEST"}


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_forbidden_system(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_test=False,
                is_system=True,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_SYSTEM"}


@pytest.mark.asyncio
async def test_admin_ui_delete_test_specialist_requires_csrf(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_test_specialist_allowed(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True, is_system=False))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_non_test_specialist_forbidden(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=False, is_system=False))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_NOT_TEST"}


@pytest.mark.asyncio
async def test_delete_system_specialist_forbidden(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=False, is_system=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "FORBIDDEN_SYSTEM"}


@pytest.mark.asyncio
async def test_execute_deletes_data(tmp_path, monkeypatch):
    await test_admin_ui_delete_test_specialist_deletes_entities_and_schedules_cleanup(tmp_path, monkeypatch)


@pytest.mark.asyncio
async def test_preflight_returns_counts(tmp_path, monkeypatch):
    await test_admin_ui_delete_test_specialist_preflight_returns_counts(tmp_path, monkeypatch)


@pytest.mark.asyncio
async def test_missing_csrf_403(tmp_path, monkeypatch):
    await test_admin_ui_delete_test_specialist_requires_csrf(tmp_path, monkeypatch)


@pytest.mark.asyncio
async def test_no_auth_404(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    response = client.post(f"/admin/ui/specialists/{specialist_id}/delete-test")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rollback_on_db_error(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        client_obj = database.Client(
            specialist_id=specialist_id,
            tg_user_id=901,
            client_code="RB001",
            client_timezone="UTC",
            timezone_source=database.ClientTimezoneSource.default_from_specialist,
        )
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True, is_system=False))
        session.add(client_obj)
        await session.flush()
        session.add(
            database.Appointment(
                specialist_id=specialist_id,
                client_id=client_obj.client_id,
                start_at_utc=now,
                end_at_utc=now + timedelta(minutes=30),
                booking_state=database.BookingState.pending,
                idempotency_key="rollback-appt-1",
            )
        )
        await session.commit()

    import sqlalchemy.ext.asyncio

    original_execute = sqlalchemy.ext.asyncio.AsyncSession.execute

    async def failing_execute(self, statement, *args, **kwargs):
        table_name = getattr(getattr(statement, "table", None), "name", None)
        if table_name == "client":
            raise RuntimeError("forced delete failure")
        return await original_execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(sqlalchemy.ext.asyncio.AsyncSession, "execute", failing_execute)

    client = TestClient(app, raise_server_exceptions=False)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 500

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        appointments_count = (
            await session.execute(select(func.count()).select_from(database.Appointment).where(database.Appointment.specialist_id == specialist_id))
        ).scalar_one()
        clients_count = (
            await session.execute(select(func.count()).select_from(database.Client).where(database.Client.specialist_id == specialist_id))
        ).scalar_one()

    assert specialist is not None
    assert appointments_count == 1
    assert clients_count == 1


@pytest.mark.asyncio
async def test_admin_specialist_detail_requires_api_key(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)

    missing_key_response = client.get(f"/admin/specialists/{specialist_id}")
    wrong_key_response = client.get(f"/admin/specialists/{specialist_id}", headers={"X-API-Key": "wrong"})

    assert missing_key_response.status_code == 403
    assert wrong_key_response.status_code == 403


@pytest.mark.asyncio
async def test_admin_specialist_detail_returns_404_for_missing_specialist(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    response = client.get(f"/admin/specialists/{uuid.uuid4()}", headers={"X-API-Key": "secret"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_specialist_detail_returns_payload_with_api_key(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_id,
                    status=database.SpecialistStatus.active,
                    created_at=now,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_id,
                    public_name="API Detail",
                    owner_tg_user_id=9123,
                    owner_tg_username="api_owner",
                    specialist_timezone="UTC",
                    slot_step_min=15,
                    max_sessions_per_day=4,
                ),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_id,
                    tg_user_id=9123,
                    tg_username="api_spec",
                    tg_first_name="Api",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get(f"/admin/specialists/{specialist_id}", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["basic"]["specialist_id"] == str(specialist_id)
    assert payload["basic"]["public_name"] == "API Detail"
    assert payload["integration"]["timezone"] == "UTC"
    assert payload["activity"]["clients_count"] == 0
    assert payload["errors"] == []

@pytest.mark.asyncio
async def test_admin_specialists_includes_specialists_without_profile_and_total(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_a, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="A",
                    owner_tg_user_id=1001,
                    owner_tg_username="a",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=1001),
                database.Specialist(specialist_id=specialist_b, status=database.SpecialistStatus.active),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_b,
                    tg_user_id=1002,
                    tg_username="b_user",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/specialists", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2

    items_by_id = {item["specialist_id"]: item for item in payload["items"]}
    assert items_by_id[str(specialist_a)]["public_name"] == "A"
    assert items_by_id[str(specialist_b)]["public_name"] == "b_user"


@pytest.mark.asyncio
async def test_admin_ui_specialists_includes_total_and_name_fallback(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_a, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="A",
                    owner_tg_user_id=2001,
                    owner_tg_username="a",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=2001),
                database.Specialist(specialist_id=specialist_b, status=database.SpecialistStatus.active),
                database.SpecialistAuthTelegram(
                    specialist_id=specialist_b,
                    tg_user_id=2002,
                    tg_first_name="BName",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/specialists", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2

    items_by_id = {item["specialist_id"]: item for item in payload["items"]}
    assert items_by_id[str(specialist_b)]["public_name"] == "BName"


@pytest.mark.asyncio
async def test_admin_logs_success_and_limit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    specialist_id = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.MessageLog(
                    created_at=now,
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=200,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="hi",
                ),
                database.MessageLog(
                    created_at=now,
                    specialist_id=specialist_id,
                    bot_id=100,
                    tg_user_id=200,
                    direction=database.LogDirection.OUT,
                    message_type="message",
                    content="ok",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/logs?limit=1000", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 500
    assert len(payload["items"]) == 2

    response_no_key = client.get("/admin/logs")
    assert response_no_key.status_code == 403


@pytest.mark.asyncio
async def test_admin_test_data_reset_dry_run(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_id,
                    public_name="Smoke",
                    owner_tg_user_id=1001,
                    owner_tg_username="smoke",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_id, tg_user_id=1001),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.post(
        "/admin/test-data/reset",
        headers={"X-API-Key": "secret"},
        json={"tg_user_ids": [1001]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert payload["counts"]["specialist"] == 1


@pytest.mark.asyncio
async def test_admin_logs_redacted_by_default(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    specialist_id = uuid.uuid4()
    token_in_content = "debug token 123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"

    async with database.async_session_factory() as session:
        session.add(
            database.MessageLog(
                created_at=now,
                specialist_id=specialist_id,
                bot_id=100,
                tg_user_id=200,
                direction=database.LogDirection.IN,
                message_type="message",
                content=token_in_content,
            )
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/logs", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["content"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_admin_ui_logs_returns_404_without_cookie_even_with_api_key(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/logs", headers={"X-API-Key": "secret"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_logs_returns_404_for_text_html_accept(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/logs",
        headers={"accept": "text/html"},
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_returns_404_for_text_html_accept(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/heartbeats",
        headers={"accept": "text/html"},
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_logs_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/logs")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_logs_returns_200_with_valid_cookie_and_redacted_items(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    token_in_content = "debug token 123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"

    async with database.async_session_factory() as session:
        session.add(
            database.MessageLog(
                specialist_id=specialist_id,
                bot_id=100,
                tg_user_id=200,
                direction=database.LogDirection.IN,
                message_type="message",
                content=token_in_content,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/logs", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    assert payload["items"][0]["content"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_admin_ui_logs_limit_clamped_to_500(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(
            database.MessageLog(
                bot_id=100,
                tg_user_id=200,
                direction=database.LogDirection.IN,
                message_type="message",
                content="hello",
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/logs?limit=1000", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 500
    assert len(payload["items"]) == 1


@pytest.mark.asyncio
async def test_admin_ui_logs_ignores_redact_param_and_stays_redacted(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    token_in_content = "debug token 123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    async with database.async_session_factory() as session:
        session.add(
            database.MessageLog(
                bot_id=100,
                tg_user_id=200,
                direction=database.LogDirection.IN,
                message_type="message",
                content=token_in_content,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/logs?redact=false", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["content"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/heartbeats")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_returns_200_with_valid_cookie(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add(
            database.ServiceHeartbeat(
                service_name="worker",
                ts=now,
                db_ok=True,
                loop_ok=True,
                latency_ms=42,
                details="ok",
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/heartbeats", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    assert payload["items"][0]["service_name"] == "worker"


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_limit_clamped_to_500(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(
            database.ServiceHeartbeat(
                service_name="worker",
                db_ok=True,
                loop_ok=True,
                latency_ms=42,
                details="ok",
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/heartbeats?limit=1000", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 500


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_service_name_filter_works(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.ServiceHeartbeat(
                    service_name="worker",
                    ts=now,
                    db_ok=True,
                    loop_ok=True,
                    latency_ms=42,
                    details="ok",
                ),
                database.ServiceHeartbeat(
                    service_name="scheduler",
                    ts=now,
                    db_ok=True,
                    loop_ok=True,
                    latency_ms=33,
                    details="ok",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/heartbeats?service_name=worker",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["service_name"] == "worker"


@pytest.mark.asyncio
async def test_admin_ui_logs_filters_is_error_and_direction(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    base_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.MessageLog(
                    created_at=base_ts,
                    bot_id=100,
                    tg_user_id=200,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    is_error=True,
                    content="err in",
                ),
                database.MessageLog(
                    created_at=base_ts + timedelta(minutes=1),
                    bot_id=100,
                    tg_user_id=201,
                    direction=database.LogDirection.OUT,
                    message_type="message",
                    is_error=False,
                    content="ok out",
                ),
                database.MessageLog(
                    created_at=base_ts + timedelta(minutes=2),
                    bot_id=100,
                    tg_user_id=202,
                    direction=database.LogDirection.OUT,
                    message_type="message",
                    is_error=True,
                    content="err out",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    err_response = client.get("/admin/ui/logs?is_error=true", cookies={"admin_session": session_cookie})
    assert err_response.status_code == 200
    err_items = err_response.json()["items"]
    assert len(err_items) == 2
    assert all(item["is_error"] is True for item in err_items)

    in_response = client.get("/admin/ui/logs?direction=IN", cookies={"admin_session": session_cookie})
    assert in_response.status_code == 200
    in_items = in_response.json()["items"]
    assert len(in_items) == 1
    assert all(item["direction"] == "IN" for item in in_items)

    out_response = client.get("/admin/ui/logs?direction=OUT", cookies={"admin_session": session_cookie})
    assert out_response.status_code == 200
    out_items = out_response.json()["items"]
    assert len(out_items) == 2
    assert all(item["direction"] == "OUT" for item in out_items)


@pytest.mark.asyncio
async def test_admin_ui_logs_pagination_offset_limit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    base_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.MessageLog(created_at=base_ts, bot_id=100, tg_user_id=1, direction=database.LogDirection.IN, message_type="message", content="a"),
                database.MessageLog(created_at=base_ts + timedelta(minutes=1), bot_id=100, tg_user_id=2, direction=database.LogDirection.IN, message_type="message", content="b"),
                database.MessageLog(created_at=base_ts + timedelta(minutes=2), bot_id=100, tg_user_id=3, direction=database.LogDirection.IN, message_type="message", content="c"),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    page1 = client.get("/admin/ui/logs?limit=2&offset=0", cookies={"admin_session": session_cookie})
    assert page1.status_code == 200
    assert len(page1.json()["items"]) == 2

    page2 = client.get("/admin/ui/logs?limit=2&offset=2", cookies={"admin_session": session_cookie})
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_since_until_filter_works(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 1, 12, 20, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.ServiceHeartbeat(service_name="worker", ts=t0, db_ok=True, loop_ok=True, latency_ms=10, details="old"),
                database.ServiceHeartbeat(service_name="worker", ts=t1, db_ok=True, loop_ok=True, latency_ms=11, details="middle"),
                database.ServiceHeartbeat(service_name="worker", ts=t2, db_ok=True, loop_ok=True, latency_ms=12, details="new"),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/heartbeats?since=2024-01-01T12:05:00Z&until=2024-01-01T12:15:00Z",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["details"] == "middle"


@pytest.mark.asyncio
async def test_admin_ui_heartbeats_pagination_offset_limit(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    t0 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.ServiceHeartbeat(service_name="worker", ts=t0, db_ok=True, loop_ok=True, latency_ms=10, details="a"),
                database.ServiceHeartbeat(service_name="worker", ts=t0 + timedelta(minutes=1), db_ok=True, loop_ok=True, latency_ms=11, details="b"),
                database.ServiceHeartbeat(service_name="worker", ts=t0 + timedelta(minutes=2), db_ok=True, loop_ok=True, latency_ms=12, details="c"),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    page1 = client.get("/admin/ui/heartbeats?limit=2&offset=0", cookies={"admin_session": session_cookie})
    assert page1.status_code == 200
    assert len(page1.json()["items"]) == 2

    page2 = client.get("/admin/ui/heartbeats?limit=2&offset=2", cookies={"admin_session": session_cookie})
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_admin_specialists_returns_404_when_admin_key_not_set(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None)
    client = TestClient(app)

    response = client.get("/admin/specialists")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_specialists_returns_403_with_wrong_key(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key="secret")
    client = TestClient(app)

    response = client.get("/admin/specialists", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_specialists_returns_dashboard_metrics(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()
    now = datetime(2024, 1, 4, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_a,
                    status=database.SpecialistStatus.active,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="Anna",
                    owner_tg_user_id=1001,
                    owner_tg_username="anna",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=1001),
                database.Specialist(
                    specialist_id=specialist_b,
                    status=database.SpecialistStatus.onboarding,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_b,
                    public_name="Bob",
                    owner_tg_user_id=1002,
                    owner_tg_username="bob",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_b, tg_user_id=1002),
                database.Client(
                    specialist_id=specialist_a,
                    tg_user_id=2001,
                    tg_username="client1",
                    display_name="Client One",
                    client_code="C1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_a,
                    tg_user_id=2002,
                    tg_username="client2",
                    display_name="Client Two",
                    client_code="C2",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_a,
                    created_at=now,
                    bot_id=111,
                    tg_user_id=2001,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="ping",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/specialists", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2

    items_by_id = {item["specialist_id"]: item for item in payload["items"]}
    item_a = items_by_id[str(specialist_a)]
    item_b = items_by_id[str(specialist_b)]

    assert item_a["clients_count"] == 2
    assert item_a["last_activity_at"] is not None

    assert item_b["clients_count"] == 0
    assert item_b["last_activity_at"] is None


@pytest.mark.asyncio
async def test_admin_ui_overview_requires_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/overview")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_overview_rejects_expired_session_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    import services.admin_ui_session as admin_ui_session

    now = 1_700_000_000
    monkeypatch.setattr(admin_ui_session.time, "time", lambda: now)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    monkeypatch.setattr(admin_ui_session.time, "time", lambda: now + (12 * 3600) + 1)
    response = client.get("/admin/ui/overview", cookies={"admin_session": session_cookie})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_overview_returns_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_VERSION", "build-xyz")
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    import admin_api

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(admin_api, "datetime", FixedDateTime)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()
    now_utc = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_a, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="A",
                    owner_tg_user_id=101,
                    owner_tg_username="a",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=101),
                database.Specialist(specialist_id=specialist_b, status=database.SpecialistStatus.active),
                database.SpecialistProfile(
                    specialist_id=specialist_b,
                    public_name="B",
                    owner_tg_user_id=102,
                    owner_tg_username="b",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_b, tg_user_id=102),
                database.Client(
                    specialist_id=specialist_a,
                    tg_user_id=201,
                    tg_username="c1",
                    display_name="C1",
                    client_code="C1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_a,
                    tg_user_id=202,
                    tg_username="c2",
                    display_name="C2",
                    client_code="C2",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_b,
                    tg_user_id=203,
                    tg_username="c3",
                    display_name="C3",
                    client_code="C3",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_a,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=111,
                    tg_user_id=201,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="ping",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/overview", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["specialists_total"] == 2
    assert payload["clients_total"] == 3
    assert payload["specialists_active_7d"] == 1
    assert payload["errors_24h"] == 0
    assert payload["computed_at_utc"] == "2026-01-20T12:00:00+00:00"
    assert payload["env"] == "local"
    assert payload["version"] == "build-xyz"


@pytest.mark.asyncio
async def test_admin_specialists_excludes_system_by_default_and_includes_by_param(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_regular = uuid.uuid4()
    specialist_system = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_regular, status=database.SpecialistStatus.active, is_system=False),
                database.SpecialistAuthTelegram(specialist_id=specialist_regular, tg_user_id=3001, tg_username="regular"),
                database.Specialist(specialist_id=specialist_system, status=database.SpecialistStatus.active, is_system=True),
                database.SpecialistAuthTelegram(specialist_id=specialist_system, tg_user_id=3002, tg_username="zumhelper_bot"),
            ]
        )
        await session.commit()

    client = TestClient(app)

    response_default = client.get("/admin/specialists", headers={"X-API-Key": "secret"})
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["total"] == 1
    assert len(payload_default["items"]) == 1

    response_with_system = client.get(
        "/admin/specialists?include_system=true",
        headers={"X-API-Key": "secret"},
    )
    assert response_with_system.status_code == 200
    payload_with_system = response_with_system.json()
    assert payload_with_system["total"] == 2
    assert len(payload_with_system["items"]) == 2




@pytest.mark.asyncio
async def test_admin_ui_specialists_excludes_system_by_default_and_includes_by_param(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_regular = uuid.uuid4()
    specialist_system = uuid.uuid4()

    now_utc = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_regular, status=database.SpecialistStatus.active, is_system=False),
                database.SpecialistAuthTelegram(specialist_id=specialist_regular, tg_user_id=3101, tg_username="regular"),
                database.Specialist(specialist_id=specialist_system, status=database.SpecialistStatus.active, is_system=True),
                database.SpecialistAuthTelegram(specialist_id=specialist_system, tg_user_id=3102, tg_username="zumhelper_bot"),
                database.Client(
                    specialist_id=specialist_regular,
                    tg_user_id=5101,
                    tg_username="client_regular",
                    display_name="Client Regular",
                    client_code="CR1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_system,
                    tg_user_id=5102,
                    tg_username="client_system",
                    display_name="Client System",
                    client_code="CS1",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_regular,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=311,
                    tg_user_id=5101,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="regular",
                ),
                database.MessageLog(
                    specialist_id=specialist_system,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=312,
                    tg_user_id=5102,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="system",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response_default = client.get("/admin/ui/specialists", cookies={"admin_session": session_cookie})
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["total"] == 1
    assert len(payload_default["items"]) == 1

    response_with_system = client.get(
        "/admin/ui/specialists?include_system=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_with_system.status_code == 200
    payload_with_system = response_with_system.json()
    assert payload_with_system["total"] == 2
    assert len(payload_with_system["items"]) == 2


@pytest.mark.asyncio
async def test_admin_ui_overview_excludes_system_by_default_and_includes_by_param(tmp_path, monkeypatch):
    monkeypatch.setenv("BUILD_VERSION", "build-xyz")
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    import admin_api

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(admin_api, "datetime", FixedDateTime)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_regular = uuid.uuid4()
    specialist_system = uuid.uuid4()
    now_utc = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=specialist_regular, status=database.SpecialistStatus.active, is_system=False),
                database.SpecialistAuthTelegram(specialist_id=specialist_regular, tg_user_id=401, tg_username="regular"),
                database.Specialist(specialist_id=specialist_system, status=database.SpecialistStatus.active, is_system=True),
                database.SpecialistAuthTelegram(specialist_id=specialist_system, tg_user_id=402, tg_username="zumhelper_bot"),
                database.Client(
                    specialist_id=specialist_regular,
                    tg_user_id=501,
                    tg_username="c_regular",
                    display_name="Regular Client",
                    client_code="CR",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.Client(
                    specialist_id=specialist_system,
                    tg_user_id=502,
                    tg_username="c_system",
                    display_name="System Client",
                    client_code="CS",
                    client_timezone="UTC",
                    timezone_source=database.ClientTimezoneSource.default_from_specialist,
                ),
                database.MessageLog(
                    specialist_id=specialist_regular,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=111,
                    tg_user_id=501,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="regular",
                ),
                database.MessageLog(
                    specialist_id=specialist_system,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=112,
                    tg_user_id=502,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="system",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response_default = client.get("/admin/ui/overview", cookies={"admin_session": session_cookie})
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["specialists_total"] == 1
    assert payload_default["clients_total"] == 1
    assert payload_default["specialists_active_7d"] == 1

    response_with_system = client.get(
        "/admin/ui/overview?include_system=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_with_system.status_code == 200
    payload_with_system = response_with_system.json()
    assert payload_with_system["specialists_total"] == 2
    assert payload_with_system["clients_total"] == 2
    assert payload_with_system["specialists_active_7d"] == 2


@pytest.mark.asyncio
async def test_admin_specialists_operational_fields_and_filters(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret")

    import admin_api

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(admin_api, "datetime", FixedDateTime)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now_utc = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()
    specialist_c = uuid.uuid4()
    specialist_system = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_a,
                    status=database.SpecialistStatus.active,
                    onboarding_master_completed_at=now_utc - timedelta(days=20),
                    onboarding_personal_completed_at=now_utc - timedelta(days=19),
                    is_system=False,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="A",
                    owner_tg_user_id=8101,
                    owner_tg_username="a",
                    specialist_timezone="Europe/Berlin",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=8101, tg_username="a"),
                database.GoogleOAuth(
                    specialist_id=specialist_a,
                    refresh_token_encrypted="enc-token-a",
                    scopes="calendar",
                    status=database.GoogleOAuthStatus.connected,
                    token_updated_at=now_utc - timedelta(days=2),
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_a,
                    calendar_id="cal_a",
                    calendar_summary="A",
                    calendar_time_zone="Europe/Berlin",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.MessageLog(
                    specialist_id=specialist_a,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=9001,
                    tg_user_id=8101,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="recent",
                ),
                database.Specialist(
                    specialist_id=specialist_b,
                    status=database.SpecialistStatus.onboarding,
                    is_system=False,
                    is_test=True,
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_b, tg_user_id=8102, tg_username="b"),
                database.Specialist(
                    specialist_id=specialist_c,
                    status=database.SpecialistStatus.active,
                    is_system=False,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_c,
                    public_name="C",
                    owner_tg_user_id=8103,
                    owner_tg_username="c",
                    specialist_timezone="UTC",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_c, tg_user_id=8103, tg_username="c"),
                database.GoogleOAuth(
                    specialist_id=specialist_c,
                    refresh_token_encrypted="enc-token-c",
                    scopes="calendar",
                    status=database.GoogleOAuthStatus.revoked,
                    token_updated_at=now_utc - timedelta(days=10),
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_c,
                    calendar_id="cal_c",
                    calendar_summary="C",
                    calendar_time_zone="UTC",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.MessageLog(
                    specialist_id=specialist_c,
                    created_at=now_utc - timedelta(days=10),
                    bot_id=9003,
                    tg_user_id=8103,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="old",
                ),
                database.Specialist(
                    specialist_id=specialist_system,
                    status=database.SpecialistStatus.active,
                    is_system=True,
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_system, tg_user_id=8104, tg_username="sys"),
            ]
        )
        await session.commit()

    client = TestClient(app)

    response_default = client.get("/admin/specialists", headers={"X-API-Key": "secret"})
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["total"] == 3

    items_by_id = {item["specialist_id"]: item for item in payload_default["items"]}
    item_a = items_by_id[str(specialist_a)]
    item_b = items_by_id[str(specialist_b)]

    assert item_a["timezone"] == "Europe/Berlin"
    assert item_a["onboarding_master_done"] is True
    assert item_a["onboarding_personal_done"] is True
    assert item_a["oauth_connected"] is True
    assert item_a["calendar_selected"] is True
    assert item_a["active_7d"] is True

    assert item_b["timezone"] is None
    assert item_b["onboarding_master_done"] is False
    assert item_b["onboarding_personal_done"] is False
    assert item_b["oauth_connected"] is False
    assert item_b["calendar_selected"] is False
    assert item_b["active_7d"] is False
    assert item_a["is_test"] is False
    assert item_b["is_test"] is True

    response_test_only = client.get("/admin/specialists?test_only=1", headers={"X-API-Key": "secret"})
    assert response_test_only.status_code == 200
    payload_test_only = response_test_only.json()
    assert payload_test_only["total"] == 1
    assert {item["specialist_id"] for item in payload_test_only["items"]} == {str(specialist_b)}

    response_oauth_missing = client.get("/admin/specialists?oauth_missing=1", headers={"X-API-Key": "secret"})
    assert response_oauth_missing.status_code == 200
    payload_oauth_missing = response_oauth_missing.json()
    assert payload_oauth_missing["total"] == 2
    oauth_missing_ids = {item["specialist_id"] for item in payload_oauth_missing["items"]}
    assert oauth_missing_ids == {str(specialist_b), str(specialist_c)}

    response_calendar_missing = client.get("/admin/specialists?calendar_missing=true", headers={"X-API-Key": "secret"})
    assert response_calendar_missing.status_code == 200
    payload_calendar_missing = response_calendar_missing.json()
    assert payload_calendar_missing["total"] == 1
    assert {item["specialist_id"] for item in payload_calendar_missing["items"]} == {str(specialist_b)}

    response_inactive = client.get("/admin/specialists?inactive_days_gt=7", headers={"X-API-Key": "secret"})
    assert response_inactive.status_code == 200
    payload_inactive = response_inactive.json()
    assert payload_inactive["total"] == 2
    assert {item["specialist_id"] for item in payload_inactive["items"]} == {str(specialist_b), str(specialist_c)}

    response_combined = client.get(
        "/admin/specialists?include_system=1&oauth_missing=1&inactive_days_gt=7",
        headers={"X-API-Key": "secret"},
    )
    assert response_combined.status_code == 200
    payload_combined = response_combined.json()
    assert payload_combined["total"] == 3
    assert {item["specialist_id"] for item in payload_combined["items"]} == {
        str(specialist_b),
        str(specialist_c),
        str(specialist_system),
    }


@pytest.mark.asyncio
async def test_admin_ui_specialists_operational_payload_and_filters(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    import admin_api

    class FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            fixed = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
            if tz is None:
                return fixed.replace(tzinfo=None)
            return fixed.astimezone(tz)

    monkeypatch.setattr(admin_api, "datetime", FixedDateTime)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now_utc = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)
    specialist_a = uuid.uuid4()
    specialist_b = uuid.uuid4()
    specialist_c = uuid.uuid4()

    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(
                    specialist_id=specialist_a,
                    status=database.SpecialistStatus.active,
                    onboarding_master_completed_at=now_utc - timedelta(days=10),
                    onboarding_personal_completed_at=now_utc - timedelta(days=9),
                    is_system=False,
                ),
                database.SpecialistProfile(
                    specialist_id=specialist_a,
                    public_name="A",
                    owner_tg_user_id=9101,
                    owner_tg_username="a",
                    specialist_timezone="Europe/Berlin",
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_a, tg_user_id=9101, tg_username="a"),
                database.GoogleOAuth(
                    specialist_id=specialist_a,
                    refresh_token_encrypted="enc-token-a",
                    scopes="calendar",
                    status=database.GoogleOAuthStatus.connected,
                    token_updated_at=now_utc - timedelta(days=2),
                ),
                database.SpecialistCalendarSettings(
                    specialist_id=specialist_a,
                    calendar_id="cal_a",
                    calendar_summary="A",
                    calendar_time_zone="Europe/Berlin",
                    source=database.SpecialistCalendarSource.selected,
                ),
                database.MessageLog(
                    specialist_id=specialist_a,
                    created_at=now_utc - timedelta(days=1),
                    bot_id=9911,
                    tg_user_id=9101,
                    direction=database.LogDirection.IN,
                    message_type="message",
                    content="recent",
                ),
                database.Specialist(
                    specialist_id=specialist_b,
                    status=database.SpecialistStatus.onboarding,
                    is_system=False,
                    is_test=True,
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_b, tg_user_id=9102, tg_username="b"),
                database.Specialist(
                    specialist_id=specialist_c,
                    status=database.SpecialistStatus.active,
                    is_system=True,
                ),
                database.SpecialistAuthTelegram(specialist_id=specialist_c, tg_user_id=9103, tg_username="sys"),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response_default = client.get("/admin/ui/specialists", cookies={"admin_session": session_cookie})
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["total"] == 2

    items_by_id = {item["specialist_id"]: item for item in payload_default["items"]}
    assert str(specialist_a) in items_by_id
    assert str(specialist_b) in items_by_id

    for item in payload_default["items"]:
        assert "timezone" in item
        assert "onboarding_master_done" in item
        assert "onboarding_personal_done" in item
        assert "oauth_connected" in item
        assert "calendar_selected" in item
        assert "active_7d" in item
        assert "email" in item
        assert "is_system" in item
        assert "is_test" in item

    item_a = items_by_id[str(specialist_a)]
    item_b = items_by_id[str(specialist_b)]

    assert item_a["oauth_connected"] is True
    assert item_a["calendar_selected"] is True
    assert item_a["timezone"] == "Europe/Berlin"
    assert item_a["active_7d"] is True

    assert item_b["oauth_connected"] is False
    assert item_b["calendar_selected"] is False
    assert item_b["timezone"] is None
    assert item_b["active_7d"] is False
    assert item_a["is_test"] is False
    assert item_b["is_test"] is True

    response_test_only = client.get(
        "/admin/ui/specialists?test_only=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_test_only.status_code == 200
    payload_test_only = response_test_only.json()
    assert payload_test_only["total"] == 1
    assert {item["specialist_id"] for item in payload_test_only["items"]} == {str(specialist_b)}

    response_oauth_missing = client.get(
        "/admin/ui/specialists?oauth_missing=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_oauth_missing.status_code == 200
    payload_oauth_missing = response_oauth_missing.json()
    assert payload_oauth_missing["total"] == 1
    assert {item["specialist_id"] for item in payload_oauth_missing["items"]} == {str(specialist_b)}

    response_calendar_missing = client.get(
        "/admin/ui/specialists?calendar_missing=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_calendar_missing.status_code == 200
    payload_calendar_missing = response_calendar_missing.json()
    assert payload_calendar_missing["total"] == 1
    assert {item["specialist_id"] for item in payload_calendar_missing["items"]} == {str(specialist_b)}

    response_calendar_missing_with_system = client.get(
        "/admin/ui/specialists?include_system=1&calendar_missing=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_calendar_missing_with_system.status_code == 200
    payload_calendar_missing_with_system = response_calendar_missing_with_system.json()
    assert payload_calendar_missing_with_system["total"] == 2
    assert {item["specialist_id"] for item in payload_calendar_missing_with_system["items"]} == {
        str(specialist_b),
        str(specialist_c),
    }

    response_inactive = client.get(
        "/admin/ui/specialists?inactive_days_gt=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_inactive.status_code == 200
    payload_inactive = response_inactive.json()
    assert payload_inactive["total"] == 1
    assert {item["specialist_id"] for item in payload_inactive["items"]} == {str(specialist_b)}

    response_include_system = client.get(
        "/admin/ui/specialists?include_system=1",
        cookies={"admin_session": session_cookie},
    )
    assert response_include_system.status_code == 200
    payload_include_system = response_include_system.json()
    assert payload_include_system["total"] == 3


@pytest.mark.asyncio
async def test_admin_ui_audit_log_returns_404_without_cookie(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.get("/admin/ui/audit-log")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_ui_audit_log_returns_200_with_valid_cookie_and_sanitized_payload(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    target_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.AdminAuditLog(
                admin_subject="cookie_session",
                action="disable_specialist",
                target_type="specialist",
                target_id=target_id,
                success=True,
                payload_json={
                    "access_token": "secret",
                    "refresh_token": "secret",
                    "secrets": {"x": 1},
                    "tokens": ["a", "b"],
                    "safe": "ok",
                },
                error_code=None,
                error_message=None,
            )
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/audit-log", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 100
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["action"] == "disable_specialist"
    assert item["target_id"] == str(target_id)
    assert item["success"] is True
    assert item["payload"] == {"safe": "ok"}


@pytest.mark.asyncio
async def test_admin_ui_audit_log_filters_working(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    target_a = uuid.uuid4()
    target_b = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="disable_specialist",
                    target_type="specialist",
                    target_id=target_a,
                    success=True,
                    payload_json={"safe": 1},
                ),
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="enable_specialist",
                    target_type="specialist",
                    target_id=target_b,
                    success=False,
                    payload_json={"safe": 2},
                    error_code="FORBIDDEN_SYSTEM",
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        f"/admin/ui/audit-log?action=enable_specialist&success=false&target_id={target_b}",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["action"] == "enable_specialist"
    assert payload["items"][0]["target_id"] == str(target_b)
    assert payload["items"][0]["success"] is False


@pytest.mark.asyncio
async def test_admin_ui_audit_log_limit_clamped_to_500(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/audit-log?limit=1000", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 500
    assert payload["offset"] == 0


@pytest.mark.asyncio
async def test_admin_ui_audit_log_filter_action_returns_only_matching_rows(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="disable_specialist",
                    target_type="specialist",
                    target_id=uuid.uuid4(),
                    success=True,
                    payload_json={"safe": 1},
                    created_at=now,
                ),
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="enable_specialist",
                    target_type="specialist",
                    target_id=uuid.uuid4(),
                    success=True,
                    payload_json={"safe": 2},
                    created_at=now + timedelta(minutes=1),
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/audit-log?action=enable_specialist",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["action"] == "enable_specialist"


@pytest.mark.asyncio
async def test_admin_ui_audit_log_filter_success_returns_only_true_rows(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="disable_specialist",
                    target_type="specialist",
                    target_id=uuid.uuid4(),
                    success=True,
                    payload_json={"safe": 1},
                    created_at=now,
                ),
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action="enable_specialist",
                    target_type="specialist",
                    target_id=uuid.uuid4(),
                    success=False,
                    payload_json={"safe": 2},
                    created_at=now + timedelta(minutes=1),
                ),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/audit-log?success=true",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["success"] is True


@pytest.mark.asyncio
async def test_admin_ui_audit_log_pagination_limit_2_offset_2_returns_correct_rows(tmp_path, monkeypatch):
    app, database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    actions = ["a0", "a1", "a2", "a3", "a4"]
    async with database.async_session_factory() as session:
        for idx, action in enumerate(actions):
            session.add(
                database.AdminAuditLog(
                    admin_subject="cookie_session",
                    action=action,
                    target_type="specialist",
                    target_id=uuid.uuid4(),
                    success=True,
                    payload_json={"idx": idx},
                    created_at=base_time + timedelta(minutes=idx),
                )
            )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(
        "/admin/ui/audit-log?limit=2&offset=2",
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 2
    # Order is created_at DESC, so after a4,a3 then offset 2 yields a2,a1
    assert [item["action"] for item in payload["items"]] == ["a2", "a1"]
