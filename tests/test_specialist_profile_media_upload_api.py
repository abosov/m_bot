import asyncio
import importlib
import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text


def _load_web_app(tmp_path, monkeypatch):
    db_path = tmp_path / "specialist_profile_media_upload.db"
    uploads_path = tmp_path / "uploads"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "invalid-token")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("BASE_URL", "http://localhost")
    monkeypatch.setenv("PUBLIC_SITE_URL", "http://localhost")
    monkeypatch.setenv("PROFILE_UPLOADS_DIR", str(uploads_path))
    monkeypatch.setenv("PROFILE_PHOTO_MAX_BYTES", "1024")
    monkeypatch.setenv("PROFILE_DOCUMENT_MAX_BYTES", "2048")

    import config
    import database
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(web_server)
    return web_server, database, uploads_path


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


def test_upload_photo_unauthorized_returns_401(tmp_path, monkeypatch):
    web_server, _database, _uploads = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", b"abc", "image/png")},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_upload_photo_replace_logic_keeps_single_photo(tmp_path, monkeypatch):
    web_server, database, uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    first = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", b"png-content-1", "image/png")},
        cookies=cookies,
    )
    assert first.status_code == 200

    second = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar2.png", b"png-content-2", "image/png")},
        cookies=cookies,
    )
    assert second.status_code == 200

    media_response = client.get("/api/specialist/profile/media", cookies=cookies)
    assert media_response.status_code == 200
    items = media_response.json()["items"]
    photo_items = [item for item in items if item["media_type"] == "photo"]
    assert len(photo_items) == 1
    assert photo_items[0]["title"] == "Фото"

    async def _assert_db_one_photo():
        async with database.async_session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT media_type FROM specialist_public_media m
                        JOIN specialist_public_profile p ON p.id = m.profile_id
                        WHERE p.specialist_id = :sid
                        """
                    ),
                    {"sid": str(specialist_id)},
                )
            ).mappings().all()
            assert [row["media_type"] for row in rows].count("photo") == 1

    asyncio.run(_assert_db_one_photo())

    photo_dir = uploads / f"specialist/{specialist_id}/photo"
    files = [p for p in photo_dir.glob("*") if p.is_file()]
    assert len(files) == 1


def test_upload_document_adds_media_record(tmp_path, monkeypatch):
    web_server, database, _uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    response = client.post(
        "/api/specialist/profile/documents",
        files={"file": ("cert.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"title": "Сертификат"},
        cookies=cookies,
    )
    assert response.status_code == 200

    media_response = client.get("/api/specialist/profile/media", cookies=cookies)
    assert media_response.status_code == 200
    docs = [item for item in media_response.json()["items"] if item["media_type"] == "document"]
    assert len(docs) == 1
    assert docs[0]["title"] == "Сертификат"


def test_upload_photo_rejects_invalid_content_type_and_size(tmp_path, monkeypatch):
    web_server, database, _uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    invalid_type = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.txt", b"text", "text/plain")},
        cookies=cookies,
    )
    assert invalid_type.status_code == 400
    assert invalid_type.json() == {"detail": "invalid_content_type"}

    too_large = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", b"a" * 2048, "image/png")},
        cookies=cookies,
    )
    assert too_large.status_code == 400
    assert too_large.json() == {"detail": "file_too_large"}
