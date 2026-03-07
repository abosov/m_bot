import importlib
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

pytest.importorskip("aiosqlite")


def load_app(tmp_path, monkeypatch):
    db_path = tmp_path / "admin_diag.db"
    uploads_path = tmp_path / "uploads"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "test-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    monkeypatch.setenv("ADMIN_UI_PASSWORD", "ui-secret")
    monkeypatch.setenv("PROFILE_UPLOADS_DIR", str(uploads_path))

    import config
    import database
    import admin_api
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(admin_api)
    importlib.reload(web_server)
    return web_server.app, database, uploads_path


async def _seed_media(database, uploads_path):
    specialist_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    media_id = uuid.uuid4()
    missing_file_key = f"specialist/{specialist_id}/docs/missing.pdf"

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_system=False,
                is_test=False,
            )
        )
        session.add(
            database.SpecialistPublicProfile(
                id=profile_id,
                specialist_id=specialist_id,
                public_slug="diag-specialist",
                display_name="Diag Spec",
                first_name="Diag",
                middle_name="",
                last_name="Spec",
                specialization="Coach",
                hero_quote="",
                contact_telegram="",
                contact_whatsapp="",
                contact_phone="",
                contact_email="",
                client_bot_username="bot",
                is_published=False,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
            )
        )
        session.add(
            database.SpecialistPublicMedia(
                id=media_id,
                profile_id=profile_id,
                media_type="document",
                file_key=missing_file_key,
                title="Missing",
                sort_order=100,
                created_at=datetime(2024, 1, 1),
            )
        )
        await session.commit()

    orphan_path = uploads_path / "specialist" / str(uuid.uuid4()) / "docs"
    orphan_path.mkdir(parents=True, exist_ok=True)
    (orphan_path / "orphan.pdf").write_bytes(b"orphan")


def _login_admin_ui(client: TestClient) -> tuple[str, str]:
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    assert login_response.status_code == 303
    session_cookie = login_response.cookies.get("admin_session")
    csrf_cookie = login_response.cookies.get("admin_csrf")
    assert session_cookie
    assert csrf_cookie
    return session_cookie, csrf_cookie


@pytest.mark.asyncio
async def test_admin_diagnostics_orphan_media_reports_missing_and_orphan(tmp_path, monkeypatch):
    app, database, uploads_path = load_app(tmp_path, monkeypatch)
    await _seed_media(database, uploads_path)
    client = TestClient(app)
    session_cookie, csrf_cookie = _login_admin_ui(client)

    async with database.async_session_factory() as session:
        media_count_before = int((await session.execute(select(func.count()).select_from(database.SpecialistPublicMedia))).scalar_one())

    run_response = client.post(
        "/admin/ui/diagnostics/run",
        json={"check_type": "orphan_specialist_media_scan"},
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["status"] == "completed"
    codes = {item["code"] for item in payload["findings"]}
    assert "MISSING_MEDIA_FILE" in codes
    assert "ORPHAN_MEDIA_OBJECT" in codes

    async with database.async_session_factory() as session:
        media_count_after = int((await session.execute(select(func.count()).select_from(database.SpecialistPublicMedia))).scalar_one())
    assert media_count_after == media_count_before


@pytest.mark.asyncio
async def test_admin_diagnostics_server_clutter_scan_reports_dev_artifacts(tmp_path, monkeypatch):
    app, _database, _uploads_path = load_app(tmp_path, monkeypatch)
    client = TestClient(app)
    session_cookie, csrf_cookie = _login_admin_ui(client)

    _uploads_path.mkdir(parents=True, exist_ok=True)
    (_uploads_path / "artifact.tmp").write_text("tmp")
    (_uploads_path / "backup.bak").write_text("bak")

    run_response = client.post(
        "/admin/ui/diagnostics/run",
        json={"check_type": "server_clutter_scan"},
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert run_response.status_code == 200
    payload = run_response.json()

    assert payload["status"] == "completed"
    assert payload["summary"]["findings_total"] >= 2
    codes = {item["code"] for item in payload["findings"]}
    assert "TEMP_ARTIFACT" in codes
    assert "STRAY_BACKUP_FILE" in codes


@pytest.mark.asyncio
async def test_admin_diagnostics_requires_authenticated_session(tmp_path, monkeypatch):
    app, _database, _uploads_path = load_app(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.post("/admin/ui/diagnostics/run", json={"check_type": "orphan_specialist_media_scan"})

    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_admin_diagnostics_requires_csrf_for_post(tmp_path, monkeypatch):
    app, _database, _uploads_path = load_app(tmp_path, monkeypatch)
    client = TestClient(app)
    session_cookie, _csrf_cookie = _login_admin_ui(client)

    response = client.post(
        "/admin/ui/diagnostics/run",
        json={"check_type": "orphan_specialist_media_scan"},
        cookies={"admin_session": session_cookie},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_diagnostics_server_clutter_scan_is_allowlisted(tmp_path, monkeypatch):
    app, _database, uploads_path = load_app(tmp_path, monkeypatch)
    client = TestClient(app)
    session_cookie, csrf_cookie = _login_admin_ui(client)

    uploads_path.mkdir(parents=True, exist_ok=True)
    (uploads_path / "inside-allowlist.bak").write_text("inside")
    outside_file = tmp_path / "outside-allowlist.bak"
    outside_file.write_text("outside")

    run_response = client.post(
        "/admin/ui/diagnostics/run",
        json={"check_type": "server_clutter_scan"},
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )
    assert run_response.status_code == 200
    payload = run_response.json()

    refs = {item["entity_ref"] for item in payload["findings"]}
    assert any("inside-allowlist.bak" in ref for ref in refs)
    assert all("outside-allowlist.bak" not in ref for ref in refs)


@pytest.mark.asyncio
async def test_admin_diagnostics_invalid_check_type_rejected(tmp_path, monkeypatch):
    app, _database, _uploads_path = load_app(tmp_path, monkeypatch)
    client = TestClient(app)
    session_cookie, csrf_cookie = _login_admin_ui(client)

    response = client.post(
        "/admin/ui/diagnostics/run",
        json={"check_type": "../../bin/sh"},
        cookies={"admin_session": session_cookie, "admin_csrf": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie},
    )

    assert response.status_code == 422
