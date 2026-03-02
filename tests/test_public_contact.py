from fastapi.testclient import TestClient

import web_server


client = TestClient(web_server.app)


def test_public_contact_smtp_not_configured(monkeypatch):
    for key in (
        "CONTACT_SMTP_HOST",
        "CONTACT_SMTP_USER",
        "CONTACT_SMTP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    response = client.post(
        "/public/contact",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello",
            "hp": None,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "smtp_not_configured"}


def test_public_contact_honeypot_bypass_skips_smtp(monkeypatch):
    calls = {"count": 0}

    def _smtp_stub(**kwargs):
        calls["count"] += 1

    for key in (
        "CONTACT_SMTP_HOST",
        "CONTACT_SMTP_USER",
        "CONTACT_SMTP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(web_server, "_send_contact_email_smtp", _smtp_stub)

    response = client.post(
        "/public/contact",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello",
            "hp": "spam",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls["count"] == 0


def test_public_contact_success_with_mocked_smtp(monkeypatch):
    captured = {"count": 0, "kwargs": {}}

    def _smtp_stub(**kwargs):
        captured["count"] += 1
        captured["kwargs"] = kwargs

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setattr(web_server, "_send_contact_email_smtp", _smtp_stub)

    response = client.post(
        "/public/contact",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello",
            "hp": "",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured["count"] == 1

    subject = captured["kwargs"]["subject"]
    body = captured["kwargs"]["body"]
    assert "Alice" in subject
    assert "alice@example.com" in subject
    assert "name: Alice" in body
    assert "email: alice@example.com" in body
    assert "request_id:" in body
