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
            "hp": "",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "smtp_not_configured"}


def test_public_contact_honeypot_skips_smtp_without_env(monkeypatch):
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


def test_public_contact_success_uses_mocked_smtp(monkeypatch):
    captured = {"count": 0, "kwargs": {}}

    def _smtp_stub(**kwargs):
        captured["count"] += 1
        captured["kwargs"] = kwargs

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CONTACT_SMTP_PORT", "2525")
    monkeypatch.setenv("CONTACT_SMTP_TIMEOUT_SECONDS", "7")
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
    assert captured["kwargs"]["smtp_host"] == "smtp.example.com"
    assert captured["kwargs"]["smtp_port"] == 2525
    assert captured["kwargs"]["smtp_timeout_seconds"] == 7


def test_send_contact_email_smtp_uses_ssl_on_465(monkeypatch):
    calls = {"ssl": None}

    class _DummySmtp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            return None

        def login(self, *_):
            return None

        def sendmail(self, *_):
            return None

    def _smtp_ssl(host, port, timeout):
        calls["ssl"] = {"host": host, "port": port, "timeout": timeout}
        return _DummySmtp()

    monkeypatch.setattr(web_server.smtplib, "SMTP_SSL", _smtp_ssl)

    web_server._send_contact_email_smtp(
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_user="mailer",
        smtp_password="secret",
        smtp_from="from@example.com",
        smtp_to="to@example.com",
        smtp_timeout_seconds=9,
        subject="subject",
        body="body",
    )

    assert calls["ssl"] == {"host": "smtp.example.com", "port": 465, "timeout": 9}


def test_send_contact_email_smtp_fallback_without_starttls(monkeypatch):
    calls = {"ehlo": 0, "starttls": 0, "login": 0, "sendmail": 0}

    class _DummySmtp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            calls["ehlo"] += 1

        def starttls(self):
            calls["starttls"] += 1
            raise web_server.smtplib.SMTPNotSupportedError("no tls")

        def login(self, *_):
            calls["login"] += 1

        def sendmail(self, *_):
            calls["sendmail"] += 1

    monkeypatch.setattr(web_server.smtplib, "SMTP", lambda *args, **kwargs: _DummySmtp())

    web_server._send_contact_email_smtp(
        smtp_host="smtp.example.com",
        smtp_port=2525,
        smtp_user="mailer",
        smtp_password="secret",
        smtp_from="from@example.com",
        smtp_to="to@example.com",
        smtp_timeout_seconds=8,
        subject="subject",
        body="body",
    )

    assert calls == {"ehlo": 1, "starttls": 1, "login": 1, "sendmail": 1}
