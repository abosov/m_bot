import importlib
from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
import pytest

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
async def test_admin_login_sets_cookie_for_correct_password(tmp_path, monkeypatch):
    app, _database = load_app(tmp_path, monkeypatch, admin_key=None, admin_ui_password="ui-secret")
    client = TestClient(app)

    response = client.post("/admin/login", data={"password": "ui-secret"}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    assert "admin_session=" in response.headers["set-cookie"]


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
    assert "<p>Environment: local</p>" in response.text
    assert "<p>Server time (UTC):" in response.text
    assert "<p>Version: build-123</p>" in response.text
    assert "<div id='admin-overview'>Loading overview…</div>" in response.text
    assert "const url='/admin/ui/overview?'+params.toString();" in response.text
    assert "id='specialists-table'" in response.text


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
