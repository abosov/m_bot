from fastapi.testclient import TestClient

import web_server


def test_healthz_contains_build_info(monkeypatch):
    monkeypatch.setattr(
        web_server,
        "get_build_info",
        lambda: {
            "version": "1-abc123-2026-02-12T00:00:00Z",
            "build_number": 1,
            "commit_sha": "abc123",
            "build_date_utc": "2026-02-12T00:00:00Z",
        },
    )

    client = TestClient(web_server.app)
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "backend"
    assert payload["commit_sha"] == "abc123"
    assert payload["build_number"] == 1
