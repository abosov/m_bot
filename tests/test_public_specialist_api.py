from fastapi.testclient import TestClient

import web_server


client = TestClient(web_server.app)


def test_get_public_specialist_profile(monkeypatch):
    payload = {
        "profile": {
            "id": "p1",
            "public_slug": "TsarevaE_12",
            "display_name": "Екатерина Царева",
            "specialization": "Психолог",
            "is_published": True,
            "private_notes": "must_not_leak",
        },
        "blocks": [{"block_type": "about", "content": "about text"}],
        "media": [{"media_type": "photo", "file_key": "files/a.jpg"}],
        "reviews": [{"author": "A", "text": "Отлично"}],
    }

    async def _service_found(slug: str):
        assert slug == "TsarevaE_12"
        return payload

    monkeypatch.setattr("backend.api.public_specialist.get_public_specialist_by_slug", _service_found)

    response = client.get("/api/public/specialists/TsarevaE_12")

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"profile", "blocks", "media", "reviews"}
    assert data["profile"]["public_slug"] == "TsarevaE_12"
    assert "private_notes" not in data["profile"]

    async def _service_missing(slug: str):
        assert slug == "TsarevaE_12"
        return None

    monkeypatch.setattr("backend.api.public_specialist.get_public_specialist_by_slug", _service_missing)
    response_missing = client.get("/api/public/specialists/TsarevaE_12")
    assert response_missing.status_code == 404

    async def _service_unpublished(slug: str):
        assert slug == "TsarevaE_12"
        return {
            "profile": {"public_slug": slug, "display_name": "X", "is_published": False},
            "blocks": [],
            "media": [],
            "reviews": [],
        }

    monkeypatch.setattr("backend.api.public_specialist.get_public_specialist_by_slug", _service_unpublished)
    response_unpublished = client.get("/api/public/specialists/TsarevaE_12")
    assert response_unpublished.status_code == 404
