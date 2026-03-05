import asyncio
import importlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text


def _load_web_app(tmp_path, monkeypatch):
    db_path = tmp_path / "specialist_profile_private.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "invalid-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")

    import config
    import database
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(web_server)
    return web_server, database


def test_specialist_profile_private_requires_cookie(tmp_path, monkeypatch):
    web_server, _database = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.get("/api/specialist/profile")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


async def _prepare_specialist(database):
    specialist_id = uuid.uuid4()
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(database.Specialist(specialist_id=specialist_id, status=database.SpecialistStatus.onboarding, specialization="Психолог"))
        session.add(
            database.SpecialistProfile(
                specialist_id=specialist_id,
                public_name="Иван Иванов",
                owner_tg_user_id=777,
                owner_tg_username="spec",
                specialist_timezone="Europe/Moscow",
            )
        )
        await session.commit()

    return specialist_id


def test_first_get_creates_draft_profile_and_returns_values(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)

    response = client.get(
        "/api/specialist/profile",
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: cookie},
    )

    assert response.status_code == 200
    assert response.json() == {
        "first_name": "Иван",
        "middle_name": "",
        "last_name": "Иванов",
        "specialization": "Психолог",
        "hero_quote": "",
        "about": "",
        "education": "",
        "services": "",
        "reviews": "",
    }

    async def _assert_profile_created():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT display_name, first_name, middle_name, last_name, is_published FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert profile is not None
            assert profile["is_published"] in (False, 0)
            assert profile["display_name"] == "Иван Иванов"
            assert profile["first_name"] == "Иван"
            assert profile["middle_name"] is None
            assert profile["last_name"] == "Иванов"

    asyncio.run(_assert_profile_created())


def test_put_then_get_returns_updated_values(tmp_path, monkeypatch):
    web_server, database = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))

    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    payload = {
        "first_name": "Анна",
        "middle_name": "Сергеевна",
        "last_name": "Петрова",
        "specialization": "Психотерапевт",
        "hero_quote": "С заботой о вашем состоянии",
        "about": "Текст о себе",
        "education": "МГУ, факультет психологии",
        "services": "Консультация 60 минут",
        "reviews": "Очень помогли",
    }

    put_response = client.put("/api/specialist/profile", json=payload, cookies=cookies)
    assert put_response.status_code == 200

    get_response = client.get("/api/specialist/profile", cookies=cookies)
    assert get_response.status_code == 200
    assert get_response.json() == payload

    async def _assert_blocks_saved():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT id, display_name, first_name, middle_name, last_name, specialization FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).mappings().first()
            assert profile is not None
            assert profile["display_name"] == "Анна Сергеевна Петрова"
            assert profile["first_name"] == "Анна"
            assert profile["middle_name"] == "Сергеевна"
            assert profile["last_name"] == "Петрова"
            assert profile["specialization"] == "Психотерапевт"

            blocks = (
                await session.execute(
                    text("SELECT block_type, content FROM specialist_public_block WHERE profile_id = :profile_id"),
                    {"profile_id": profile["id"]},
                )
            ).mappings().all()
            by_type = {b["block_type"]: b["content"] for b in blocks}
            assert by_type == {
                "about": "Текст о себе",
                "education": "МГУ, факультет психологии",
                "services": "Консультация 60 минут",
                "reviews": "Очень помогли",
            }

    asyncio.run(_assert_blocks_saved())
