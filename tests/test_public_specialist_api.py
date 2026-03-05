from __future__ import annotations

from fastapi.testclient import TestClient

import web_server


client = TestClient(web_server.app)


def test_public_specialist_invalid_slug_format():
    response = client.get("/api/public/specialists/invalid-slug")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_slug_format"


def test_public_specialist_invalid_slug_suffix_range():
    response_low = client.get("/api/public/specialists/TsarevaE_09")
    assert response_low.status_code == 400
    assert response_low.json()["detail"] == "invalid_slug_suffix_range"

    response_high = client.get("/api/public/specialists/TsarevaE_31")
    assert response_high.status_code == 400
    assert response_high.json()["detail"] == "invalid_slug_suffix_range"


def test_public_specialist_not_found(monkeypatch):
    async def _service_missing(slug: str):
        assert slug == "TsarevaE_12"
        return None

    monkeypatch.setattr("backend.api.public_specialist.get_public_specialist_by_slug", _service_missing)

    response = client.get("/api/public/specialists/TsarevaE_12")
    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


def test_public_specialist_unpublished_returns_404(monkeypatch):
    # Service-level contract is published-only; unpublished profiles are hidden as not found.
    async def _service_unpublished_filtered(slug: str):
        assert slug == "TsarevaE_12"
        return None

    monkeypatch.setattr(
        "backend.api.public_specialist.get_public_specialist_by_slug",
        _service_unpublished_filtered,
    )

    response = client.get("/api/public/specialists/TsarevaE_12")
    assert response.status_code == 404
    assert response.json()["detail"] == "not_found"


def test_public_specialist_success_and_no_raw_file_key(monkeypatch):
    payload = {
        "profile": {
            "id": "p1",
            "public_slug": "TsarevaE_12",
            "display_name": "Евгения Царёва",
            "specialization": "Психолог, ЭФТ",
            "hero_quote": "Можно по-другому.",
            "contacts": {
                "telegram": "evgenia_tsareva",
                "whatsapp": "+79990000000",
                "phone": "+79991112233",
                "email": "info@example.com",
            },
            "client_bot_username": "zumbot_client_bot",
        },
        "blocks": [
            {
                "block_type": "about",
                "content": "О себе текст",
                "sort_order": 10,
                "updated_at": "2026-03-12T10:00:00",
            }
        ],
        "media": [
            {
                "media_type": "photo",
                "file_key": "private/key.jpg",
                "title": "Фото",
                "sort_order": 10,
                "created_at": "2026-03-12T10:00:00",
            }
        ],
    }

    async def _service_found(slug: str):
        assert slug == "TsarevaE_12"
        return payload

    monkeypatch.setattr("backend.api.public_specialist.get_public_specialist_by_slug", _service_found)

    response = client.get("/api/public/specialists/TsarevaE_12")
    assert response.status_code == 200

    data = response.json()
    assert set(data.keys()) == {"profile", "blocks", "media"}
    assert data["profile"]["public_slug"] == "TsarevaE_12"
    assert data["profile"]["display_name"] == "Евгения Царёва"
    assert len(data["blocks"]) == 1
    assert len(data["media"]) == 1
    assert data["media"][0]["media_type"] == "photo"
    assert data["media"][0]["title"] == "Фото"
    assert data["media"][0]["url"] is None
    assert "file_key" not in data["media"][0]
    assert "file_key" not in str(data).lower()
