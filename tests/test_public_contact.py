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
    sent: list[dict] = []

    def _smtp_stub(**kwargs):
        sent.append(kwargs)

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
    assert len(sent) == 2

    main_email = sent[0]
    subject = main_email["subject"]
    body = main_email["body"]
    assert "Alice" in subject
    assert "alice@example.com" in subject
    assert "name: Alice" in body
    assert "email: alice@example.com" in body
    assert "request_id:" in body
    assert main_email["smtp_host"] == "smtp.example.com"
    assert main_email["smtp_port"] == 2525
    assert main_email["smtp_timeout_seconds"] == 7




def test_public_contact_success_sends_autoreply(monkeypatch):
    sent: list[dict] = []

    def _smtp_stub(**kwargs):
        sent.append(kwargs)

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "inbox@example.com")
    monkeypatch.setenv("CONTACT_FROM_EMAIL", "from@example.com")
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
    assert len(sent) == 2

    main_email, autoreply = sent
    assert main_email["smtp_to"] == "inbox@example.com"
    assert autoreply["smtp_to"] == "alice@example.com"
    assert autoreply["smtp_from"] == "from@example.com"
    assert autoreply["reply_to"] == "from@example.com"
    assert autoreply["subject"] == "Мы получили ваше сообщение — Zumbot"
    assert "Номер обращения:" in autoreply["body"]




def test_public_contact_autoreply_disabled_by_env(monkeypatch):
    sent: list[dict] = []

    def _smtp_stub(**kwargs):
        sent.append(kwargs)

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "inbox@example.com")
    monkeypatch.setenv("CONTACT_AUTOREPLY_ENABLED", "false")
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
    assert len(sent) == 1
    assert sent[0]["smtp_to"] == "inbox@example.com"

def test_public_contact_autoreply_failure_does_not_break_ok(monkeypatch):
    calls = {"count": 0}
    alerts: list[dict] = []

    def _smtp_stub(**kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("smtp down")

    async def _notify_stub(where, exc, context=None, **kwargs):
        alerts.append({"where": where, "exc": exc, "context": context or {}})

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setattr(web_server, "_send_contact_email_smtp", _smtp_stub)
    monkeypatch.setattr(web_server, "notify_exception", _notify_stub)

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
    assert calls["count"] == 2
    assert len(alerts) == 1
    assert alerts[0]["where"] == "web.contact_form_autoreply"
    assert "message" not in alerts[0]["context"]


def test_public_contact_autoreply_not_sent_when_main_send_fails(monkeypatch):
    calls = {"count": 0}

    def _smtp_stub(**kwargs):
        calls["count"] += 1
        raise RuntimeError("smtp down")

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
    assert response.json() == {"ok": False, "error": "smtp_send_failed"}
    assert calls["count"] == 1


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
