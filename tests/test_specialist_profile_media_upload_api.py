import asyncio
import importlib
import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from PIL import Image


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
    monkeypatch.setenv("ADMIN_UI_PASSWORD", "admin-pass")
    monkeypatch.setenv("PROFILE_UPLOADS_DIR", str(uploads_path))
    monkeypatch.setenv("PROFILE_PHOTO_MAX_BYTES", "100000")
    monkeypatch.setenv("PROFILE_DOCUMENT_MAX_BYTES", "2048")

    import config
    import database
    import web_server

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(web_server)
    return web_server, database, uploads_path


async def _prepare_specialist(database, *, is_test: bool = False):
    specialist_id = uuid.uuid4()
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.onboarding,
                specialization="Психолог",
                is_test=is_test,
            )
        )
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




def _png_bytes(color=(120, 130, 140)):
    image = Image.new("RGB", (1000, 1000), color)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_photo_unauthorized_returns_401(tmp_path, monkeypatch):
    web_server, _database, _uploads = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", _png_bytes(), "image/png")},
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
        files={"file": ("avatar.png", _png_bytes((100,100,100)), "image/png")},
        cookies=cookies,
    )
    assert first.status_code == 200

    second = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar2.png", _png_bytes((120,120,120)), "image/png")},
        cookies=cookies,
    )
    assert second.status_code == 200

    media_response = client.get("/api/specialist/profile/media", cookies=cookies)
    assert media_response.status_code == 200
    items = media_response.json()["items"]
    photo_items = [item for item in items if item["media_type"] == "photo"]
    assert len(photo_items) == 1
    assert photo_items[0]["title"] == "Фото"
    assert photo_items[0]["file_key"] == f"media/specialists/{specialist_id}/profile_photo.jpg"

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

    photo_path = uploads / f"media/specialists/{specialist_id}/profile_photo.jpg"
    assert photo_path.is_file()


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
    assert docs[0]["file_key"] is None


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
        files={"file": ("avatar.png", b"a" * 120000, "image/png")},
        cookies=cookies,
    )
    assert too_large.status_code == 413
    assert too_large.json() == {"detail": "file_too_large"}


def test_upload_photo_db_failure_does_not_replace_existing_file_and_cleans_temp(tmp_path, monkeypatch):
    web_server, database, uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app, raise_server_exceptions=False)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    final_path = uploads / f"media/specialists/{specialist_id}/profile_photo.jpg"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(b"old-photo")

    import backend.api.specialist_profile_private as specialist_api

    async def _boom(*args, **kwargs):
        raise RuntimeError("db_failed")

    monkeypatch.setattr(specialist_api, "replace_specialist_profile_photo", _boom)

    response = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", _png_bytes((10, 20, 30)), "image/png")},
        cookies=cookies,
    )
    assert response.status_code == 500
    assert final_path.read_bytes() == b"old-photo"

    temp_files = list((uploads / f"media/specialists/{specialist_id}").glob("*.tmp"))
    assert temp_files == []


def test_public_media_endpoint_serves_old_and_new_photo_keys_and_rejects_documents(tmp_path, monkeypatch):
    web_server, database, uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app)

    async def _ensure_public_profile():
        async with database.async_session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_profile (
                        id, specialist_id, public_slug, display_name, first_name, middle_name, last_name,
                        specialization, hero_quote, contact_telegram, contact_whatsapp, contact_phone, contact_email,
                        client_bot_username, is_published, created_at, updated_at
                    ) VALUES (
                        :id, :specialist_id, :public_slug, :display_name, :first_name, :middle_name, :last_name,
                        :specialization, NULL, NULL, NULL, NULL, NULL,
                        :client_bot_username, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "specialist_id": str(specialist_id),
                    "public_slug": f"Spec_{str(specialist_id).replace('-', '')[:2]}12",
                    "display_name": "Иван Иванов",
                    "first_name": "Иван",
                    "middle_name": None,
                    "last_name": "Иванов",
                    "specialization": "Психолог",
                    "client_bot_username": "zumbot_client_bot",
                },
            )
            await session.commit()

    asyncio.run(_ensure_public_profile())

    old_key = f"specialist/{specialist_id}/photo/legacy_avatar.png"
    new_key = f"media/specialists/{specialist_id}/profile_photo.jpg"
    doc_key = f"specialist/{specialist_id}/docs/cert.pdf"

    (uploads / old_key).parent.mkdir(parents=True, exist_ok=True)
    legacy_png = io.BytesIO()
    Image.new("RGB", (10, 10), (255, 0, 0)).save(legacy_png, format="PNG")
    (uploads / old_key).write_bytes(legacy_png.getvalue())
    (uploads / new_key).parent.mkdir(parents=True, exist_ok=True)
    new_jpeg = io.BytesIO()
    Image.new("RGB", (10, 10), (0, 255, 0)).save(new_jpeg, format="JPEG")
    (uploads / new_key).write_bytes(new_jpeg.getvalue())
    (uploads / doc_key).parent.mkdir(parents=True, exist_ok=True)
    (uploads / doc_key).write_bytes(b"doc")

    async def _seed_media_rows():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT id FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).scalar_one()
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_media (id, profile_id, media_type, file_key, title, sort_order, created_at)
                    VALUES (:id1, :profile_id, 'photo', :old_key, 'old', 10, CURRENT_TIMESTAMP),
                           (:id2, :profile_id, 'photo', :new_key, 'new', 11, CURRENT_TIMESTAMP),
                           (:id3, :profile_id, 'document', :doc_key, 'doc', 100, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id1": str(uuid.uuid4()),
                    "id2": str(uuid.uuid4()),
                    "id3": str(uuid.uuid4()),
                    "profile_id": str(profile),
                    "old_key": old_key,
                    "new_key": new_key,
                    "doc_key": doc_key,
                },
            )
            await session.commit()

    asyncio.run(_seed_media_rows())

    old_response = client.get(f"/media/{old_key}")
    assert old_response.status_code == 200
    assert old_response.headers["content-type"].startswith("image/png")

    canonical_photo_path = f"specialists/{specialist_id}/profile_photo.jpg"
    canonical_response = client.get(f"/media/{canonical_photo_path}")
    assert canonical_response.status_code == 200
    assert canonical_response.headers["content-type"].startswith("image/jpeg")

    new_response = client.get(f"/media/{new_key}")
    assert new_response.status_code == 200
    assert new_response.headers["content-type"].startswith("image/jpeg")
    assert client.get(f"/media/{doc_key}").status_code == 404
    assert client.get("/media/not-a-valid-path").status_code == 404

    missing_old = f"specialist/{specialist_id}/photo/missing.png"
    async def _seed_missing():
        async with database.async_session_factory() as session:
            profile = (
                await session.execute(
                    text("SELECT id FROM specialist_public_profile WHERE specialist_id = :sid"),
                    {"sid": str(specialist_id)},
                )
            ).scalar_one()
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_media (id, profile_id, media_type, file_key, title, sort_order, created_at)
                    VALUES (:id, :profile_id, 'photo', :missing_key, 'missing', 12, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": str(uuid.uuid4()), "profile_id": str(profile), "missing_key": missing_old},
            )
            await session.commit()
    asyncio.run(_seed_missing())
    assert client.get(f"/media/{missing_old}").status_code == 404


def test_admin_delete_test_specialist_removes_media_rows_and_photo_file(tmp_path, monkeypatch):
    web_server, database, uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database, is_test=True))
    client = TestClient(web_server.app)

    cookie = web_server.admin_ui_session.sign_admin_session_cookie(ttl_hours=12)
    csrf_token = "csrf-token"
    cookies = {
        web_server.ADMIN_UI_COOKIE_NAME: cookie,
        web_server.ADMIN_UI_CSRF_COOKIE_NAME: csrf_token,
    }

    async def _force_is_test_flag():
        async with database.async_session_factory() as session:
            await session.execute(
                text("UPDATE specialist SET is_test = 1 WHERE specialist_id = :sid"),
                {"sid": str(specialist_id)},
            )
            await session.commit()

    asyncio.run(_force_is_test_flag())

    specialist_cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    upload_response = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", _png_bytes((20, 40, 60)), "image/png")},
        cookies={web_server.config.WEB_CONNECT_COOKIE_NAME: specialist_cookie},
    )
    assert upload_response.status_code == 200

    photo_key = f"media/specialists/{specialist_id}/profile_photo.jpg"
    photo_path = uploads / photo_key
    assert photo_path.is_file()

    response = client.post(
        f"/admin/ui/specialists/{specialist_id}/delete-test",
        cookies=cookies,
        headers={web_server.ADMIN_UI_CSRF_HEADER_NAME: csrf_token},
    )
    assert response.status_code == 200

    async def _assert_media_removed():
        async with database.async_session_factory() as session:
            count = (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM specialist_public_media m
                        JOIN specialist_public_profile p ON p.id = m.profile_id
                        WHERE p.specialist_id = :sid
                        """
                    ),
                    {"sid": str(specialist_id)},
                )
            ).scalar_one()
            assert int(count) == 0

    asyncio.run(_assert_media_removed())
    assert not photo_path.exists()
    assert list((uploads / f"media/specialists/{specialist_id}").glob("*")) == []


def test_delete_photo_endpoint_is_idempotent_and_keeps_documents(tmp_path, monkeypatch):
    web_server, database, uploads = _load_web_app(tmp_path, monkeypatch)
    specialist_id = asyncio.run(_prepare_specialist(database))
    client = TestClient(web_server.app)
    cookie = web_server.web_session.sign_session_cookie(specialist_id, 777)
    cookies = {web_server.config.WEB_CONNECT_COOKIE_NAME: cookie}

    upload_photo = client.post(
        "/api/specialist/profile/photo",
        files={"file": ("avatar.png", _png_bytes((10, 20, 30)), "image/png")},
        cookies=cookies,
    )
    assert upload_photo.status_code == 200

    upload_doc = client.post(
        "/api/specialist/profile/documents",
        files={"file": ("cert.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"title": "Сертификат"},
        cookies=cookies,
    )
    assert upload_doc.status_code == 200

    photo_path = uploads / f"media/specialists/{specialist_id}/profile_photo.jpg"
    assert photo_path.exists()

    delete_response = client.delete("/api/specialist/profile/photo", cookies=cookies)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}
    assert not photo_path.exists()

    media_after_delete = client.get("/api/specialist/profile/media", cookies=cookies)
    assert media_after_delete.status_code == 200
    items = media_after_delete.json()["items"]
    assert [item for item in items if item["media_type"] == "photo"] == []
    docs = [item for item in items if item["media_type"] == "document"]
    assert len(docs) == 1

    second_delete = client.delete("/api/specialist/profile/photo", cookies=cookies)
    assert second_delete.status_code == 200
    assert second_delete.json() == {"ok": True}


def test_delete_photo_unauthorized_returns_401(tmp_path, monkeypatch):
    web_server, _database, _uploads = _load_web_app(tmp_path, monkeypatch)
    client = TestClient(web_server.app)

    response = client.delete("/api/specialist/profile/photo")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}
