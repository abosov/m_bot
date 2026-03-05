from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytest.importorskip("aiosqlite")


async def _build_test_app(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "public_specialist_api.db"

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("MASTER_BOT_TOKEN", "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
    monkeypatch.setenv("ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    import config
    import database
    import services.public_specialist as public_specialist_service
    import backend.api.public_specialist as public_specialist_api

    importlib.reload(config)
    database = importlib.reload(database)
    importlib.reload(public_specialist_service)
    public_specialist_api = importlib.reload(public_specialist_api)

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    app = FastAPI()
    app.include_router(public_specialist_api.router)
    return database, app


async def _create_public_profile(
    database,
    *,
    slug: str,
    published: bool,
    with_blocks_and_media: bool,
):
    specialist_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with database.async_session_factory() as session:
        session.add(
            database.Specialist(
                specialist_id=specialist_id,
                status=database.SpecialistStatus.active,
            )
        )

        profile = database.SpecialistPublicProfile(
            specialist_id=specialist_id,
            public_slug=slug,
            display_name="Евгения Царёва",
            specialization="Психолог, ЭФТ",
            hero_quote="Можно по-другому.",
            contact_telegram="evgenia_tsareva",
            contact_whatsapp="+79990000000",
            contact_phone="+79991112233",
            contact_email="info@example.com",
            client_bot_username="zumbot_client_bot",
            is_published=published,
            created_at=now,
            updated_at=now,
        )
        session.add(profile)
        await session.flush()

        if with_blocks_and_media:
            session.add_all(
                [
                    database.SpecialistPublicBlock(
                        profile_id=profile.id,
                        block_type="about",
                        content="О себе текст",
                        sort_order=10,
                        updated_at=now,
                    ),
                    database.SpecialistPublicBlock(
                        profile_id=profile.id,
                        block_type="education",
                        content="Образование",
                        sort_order=20,
                        updated_at=now,
                    ),
                ]
            )
            session.add(
                database.SpecialistPublicMedia(
                    profile_id=profile.id,
                    media_type="photo",
                    file_key="private/secret-key.jpg",
                    title="Фото",
                    sort_order=10,
                    created_at=now,
                )
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
async def test_public_specialist_invalid_slug_suffix_range(tmp_path, monkeypatch):
    _, app = await _build_test_app(tmp_path, monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_low = await client.get("/api/public/specialists/TsarevaE_09")
        response_high = await client.get("/api/public/specialists/TsarevaE_31")

    assert response_low.status_code == 400
    assert response_low.json()["detail"] == "invalid_slug_suffix_range"
    assert response_high.status_code == 400
    assert response_high.json()["detail"] == "invalid_slug_suffix_range"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reserved_slug",
    ["pricing", "privacy", "terms", "revoke-access", "api", "static", "assets"],
)
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
    await _create_public_profile(
        database,
        slug="TsarevaE_12",
        published=False,
        with_blocks_and_media=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_public_specialist_published_profile_returns_public_response(tmp_path, monkeypatch):
    database, app = await _build_test_app(tmp_path, monkeypatch)
    await _create_public_profile(
        database,
        slug="TsarevaE_12",
        published=True,
        with_blocks_and_media=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 200

    data = response.json()
    assert set(data.keys()) == {"profile", "blocks", "media"}

    assert data["profile"]["public_slug"] == "TsarevaE_12"
    assert data["profile"]["display_name"] == "Евгения Царёва"
    assert data["profile"]["contacts"]["telegram"] == "evgenia_tsareva"

    assert len(data["blocks"]) == 2
    assert data["blocks"][0]["block_type"] == "about"

    assert len(data["media"]) == 1
    assert data["media"][0]["media_type"] == "photo"
    assert data["media"][0]["title"] == "Фото"
    assert data["media"][0]["url"] is None
    assert "file_key" not in data["media"][0]
    assert "file_key" not in str(data).lower()
