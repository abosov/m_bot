from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.tests.fixtures.public_specialist_seed import seed_public_specialist_tsareva_e12

pytest.importorskip("aiosqlite")


async def _build_test_app(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "public_specialist_api.db"

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import config
    import database
    import backend.services.public_specialist_service as public_specialist_service
    import backend.api.public_specialist as public_specialist_api

    importlib.reload(config)
    database = importlib.reload(database)
    importlib.reload(public_specialist_service)
    public_specialist_api = importlib.reload(public_specialist_api)

    async with database.engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE specialist_public_profile (
                    id TEXT PRIMARY KEY,
                    specialist_id TEXT,
                    public_slug TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    specialization TEXT NOT NULL,
                    hero_quote TEXT,
                    contact_telegram TEXT,
                    contact_whatsapp TEXT,
                    contact_phone TEXT,
                    contact_email TEXT,
                    client_bot_username TEXT NOT NULL,
                    is_published BOOLEAN NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE specialist_public_block (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    block_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sort_order INTEGER NOT NULL,
                    updated_at TEXT
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE specialist_public_media (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    title TEXT,
                    file_key TEXT,
                    sort_order INTEGER NOT NULL,
                    created_at TEXT
                )
                """
            )
        )

    app = FastAPI()
    app.include_router(public_specialist_api.router)
    return database, app


async def _create_public_profile(database, *, slug: str, published: bool, with_related: bool):
    profile_id = str(uuid.uuid4())
    specialist_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with database.async_session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO specialist_public_profile (
                    id, specialist_id, public_slug, display_name, specialization, hero_quote,
                    contact_telegram, contact_whatsapp, contact_phone, contact_email,
                    client_bot_username, is_published, created_at, updated_at
                ) VALUES (
                    :id, :specialist_id, :public_slug, :display_name, :specialization, :hero_quote,
                    :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                    :client_bot_username, :is_published, :created_at, :updated_at
                )
                """
            ),
            {
                "id": profile_id,
                "specialist_id": specialist_id,
                "public_slug": slug,
                "display_name": "Евгения Царёва",
                "specialization": "Психолог, ЭФТ",
                "hero_quote": "Можно по-другому.",
                "contact_telegram": "evgenia_tsareva",
                "contact_whatsapp": "+79990000000",
                "contact_phone": "+79991112233",
                "contact_email": "info@example.com",
                "client_bot_username": "zumbot_client_bot",
                "is_published": published,
                "created_at": now,
                "updated_at": now,
            },
        )

        if with_related:
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_block (id, profile_id, block_type, content, sort_order, updated_at)
                    VALUES (:id1, :profile_id, 'about', 'О себе текст', 10, :updated_at),
                           (:id2, :profile_id, 'education', 'Образование', 20, :updated_at)
                    """
                ),
                {"id1": str(uuid.uuid4()), "id2": str(uuid.uuid4()), "profile_id": profile_id, "updated_at": now},
            )
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_media (id, profile_id, media_type, title, file_key, sort_order, created_at)
                    VALUES (:id, :profile_id, 'photo', 'Фото', 'private/secret-key.jpg', 10, :created_at)
                    """
                ),
                {"id": str(uuid.uuid4()), "profile_id": profile_id, "created_at": now},
            )

        await session.commit()


@pytest.mark.asyncio
async def test_public_specialist_invalid_slug_format(tmp_path, monkeypatch):
    _, app = await _build_test_app(tmp_path, monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/invalid-slug")

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_slug_format"


@pytest.mark.asyncio
@pytest.mark.parametrize("reserved_slug", ["pricing", "privacy", "terms", "revoke-access", "api", "static", "assets"])
async def test_public_specialist_reserved_paths_return_invalid_slug(tmp_path, monkeypatch, reserved_slug):
    _, app = await _build_test_app(tmp_path, monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/public/specialists/{reserved_slug}")

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_slug"


@pytest.mark.asyncio
async def test_public_specialist_valid_slug_not_found_returns_404(tmp_path, monkeypatch):
    _, app = await _build_test_app(tmp_path, monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_public_specialist_unpublished_profile_returns_404(tmp_path, monkeypatch):
    database, app = await _build_test_app(tmp_path, monkeypatch)
    await _create_public_profile(database, slug="TsarevaE_12", published=False, with_related=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_public_specialist_published_profile_returns_public_response(tmp_path, monkeypatch):
    database, app = await _build_test_app(tmp_path, monkeypatch)
    async with database.async_session_factory() as session:
        await seed_public_specialist_tsareva_e12(session)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 200

    data = response.json()
    assert set(data.keys()) == {"profile", "blocks", "media", "reviews"}

    assert data["profile"]["public_slug"] == "TsarevaE_12"
    assert data["profile"]["contacts"]["telegram"] == "evgenia_tsareva"
    assert data["profile"]["profile_photo_url"] == "/media/private/demo/tsareva-photo.jpg"

    assert len(data["blocks"]) == 3
    assert [block["block_type"] for block in data["blocks"]] == ["about", "education", "services"]

    assert len(data["media"]) == 1
    assert data["media"][0]["media_type"] == "photo"
    assert data["media"][0]["url"] is None
    assert "file_key" not in data["media"][0]

    assert data["reviews"] == []


@pytest.mark.asyncio
async def test_public_specialist_prefers_canonical_hero_photo_key(tmp_path, monkeypatch):
    database, app = await _build_test_app(tmp_path, monkeypatch)
    profile_id = str(uuid.uuid4())
    specialist_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with database.async_session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO specialist_public_profile (
                    id, specialist_id, public_slug, display_name, specialization, hero_quote,
                    contact_telegram, contact_whatsapp, contact_phone, contact_email,
                    client_bot_username, is_published, created_at, updated_at
                ) VALUES (
                    :id, :specialist_id, :public_slug, :display_name, :specialization, :hero_quote,
                    :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                    :client_bot_username, :is_published, :created_at, :updated_at
                )
                """
            ),
            {
                "id": profile_id,
                "specialist_id": specialist_id,
                "public_slug": "TsarevaE_12",
                "display_name": "Евгения Царёва",
                "specialization": "Психолог",
                "hero_quote": "Можно по-другому",
                "contact_telegram": None,
                "contact_whatsapp": None,
                "contact_phone": None,
                "contact_email": None,
                "client_bot_username": "zumbot_client_bot",
                "is_published": True,
                "created_at": now,
                "updated_at": now,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO specialist_public_media (id, profile_id, media_type, title, file_key, sort_order, created_at)
                VALUES
                    (:id1, :profile_id, 'photo', 'Legacy', :legacy_key, 5, :created_at),
                    (:id2, :profile_id, 'photo', 'Hero', :hero_key, 10, :created_at)
                """
            ),
            {
                "id1": str(uuid.uuid4()),
                "id2": str(uuid.uuid4()),
                "profile_id": profile_id,
                "legacy_key": "specialist/legacy/photo.png",
                "hero_key": f"media/specialists/{specialist_id}/profile_photo.jpg",
                "created_at": now,
            },
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 200
    assert response.json()["profile"]["profile_photo_url"] == f"/media/media/specialists/{specialist_id}/profile_photo.jpg"
