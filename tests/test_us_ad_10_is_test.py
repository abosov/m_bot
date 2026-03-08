import importlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytest.importorskip("aiosqlite")


def _load_app(tmp_path, monkeypatch, *, admin_key: str | None = None, admin_ui_password: str | None = None):
    db_path = tmp_path / "us_ad_10_is_test.db"
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
    return web_server.app, database, web_server


@pytest.mark.asyncio
async def test_specialist_default_not_test(tmp_path, monkeypatch):
    _app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
            )
        )
        await session.commit()

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.is_test is False


@pytest.mark.asyncio
async def test_system_specialist_not_test(tmp_path, monkeypatch):
    _app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret")

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

    async with database.async_session_factory() as session:
        specialist = await session.get(database.Specialist, specialist_id)
        assert specialist is not None
        assert specialist.is_system is True
        assert specialist.is_test is False


@pytest.mark.asyncio
async def test_specialist_flag_exposed_in_admin_api(tmp_path, monkeypatch):
    app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    regular_id = uuid.uuid4()
    test_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=regular_id, status=database.SpecialistStatus.active, is_test=False),
                database.Specialist(specialist_id=test_id, status=database.SpecialistStatus.active, is_test=True),
            ]
        )
        await session.commit()

    client = TestClient(app)
    response = client.get("/admin/specialists", headers={"X-API-Key": "secret"})

    assert response.status_code == 200
    payload = response.json()
    by_id = {item["specialist_id"]: item for item in payload["items"]}
    assert by_id[str(regular_id)]["is_test"] is False
    assert by_id[str(test_id)]["is_test"] is True

    sensitive_keys = {"refresh_token_encrypted", "bot_token_encrypted", "webhook_secret", "api_key", "password"}
    for item in payload["items"]:
        assert sensitive_keys.isdisjoint(item.keys())


@pytest.mark.asyncio
async def test_admin_ui_specialists_returns_is_test_field(tmp_path, monkeypatch):
    app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/specialists", cookies={"admin_session": session_cookie})
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["is_test"] is True


@pytest.mark.asyncio
async def test_admin_ui_specialists_test_only_returns_only_test_accounts(tmp_path, monkeypatch):
    app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    regular_id = uuid.uuid4()
    test_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add_all(
            [
                database.Specialist(specialist_id=regular_id, status=database.SpecialistStatus.active, is_test=False),
                database.Specialist(specialist_id=test_id, status=database.SpecialistStatus.active, is_test=True),
            ]
        )
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin/ui/specialists?test_only=1", cookies={"admin_session": session_cookie})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert {item["specialist_id"] for item in payload["items"]} == {str(test_id)}
    assert all(item["is_test"] is True for item in payload["items"])


def test_production_endpoints_cannot_update_is_test():
    from backend.schemas.specialist_profile_private import SpecialistProfilePrivateUpdateRequest

    payload = SpecialistProfilePrivateUpdateRequest.model_validate(
        {
            "first_name": "QA",
            "middle_name": "",
            "last_name": "Spec",
            "specialization": "Психолог",
            "hero_quote": "",
            "about": "",
            "education": "",
            "services": "",
            "reviews": "",
            "is_test": True,
        }
    )

    dumped = payload.model_dump()
    assert "is_test" not in dumped


@pytest.mark.asyncio
async def test_admin_ui_specialist_detail_returns_is_test_field(tmp_path, monkeypatch):
    app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.active, is_test=True))
        await session.commit()

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get(f"/admin/ui/specialists/{specialist_id}", cookies={"admin_session": session_cookie})

    assert response.status_code == 200
    payload = response.json()
    assert payload["basic"]["specialist_id"] == str(specialist_id)
    assert payload["basic"]["is_test"] is True


@pytest.mark.asyncio
async def test_system_account_cannot_be_marked_as_test_by_direct_update(tmp_path, monkeypatch):
    _app, database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret")

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    specialist_id = uuid.uuid4()
    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
                is_system=True,
                is_test=False,
            )
        )
        await session.commit()

    async with database.async_session_factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    """
                    UPDATE specialist
                    SET is_test = TRUE
                    WHERE is_system = TRUE
                    """
                )
            )
            await session.commit()


def test_admin_ui_html_renders_test_badge_conditionally(tmp_path, monkeypatch):
    app, _database, _web_server = _load_app(tmp_path, monkeypatch, admin_key="secret", admin_ui_password="ui-secret")

    client = TestClient(app)
    login_response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)
    session_cookie = login_response.cookies.get("admin_session")

    response = client.get("/admin", cookies={"admin_session": session_cookie})
    assert response.status_code == 200
    assert "if(item.is_test)flags.push('<span class=\"badge badge-test\"" in response.text
    assert "if(item.is_system)flags.push('<span class=\"badge badge-system\"" in response.text
    assert 'Test specialist. Used for admin test-account workflows.' in response.text
