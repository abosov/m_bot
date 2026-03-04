import re

from fastapi.testclient import TestClient

import web_server


client = TestClient(web_server.app)


def test_site_index_returns_landing():
    response = client.get("/")

    assert response.status_code == 200
    assert "Zumbot — Calendar Booking Automation" in response.text


def test_site_pages_are_available():
    expected = {
        "/features": "Возможности Zumbot",
        "/pricing": "Тарифы",
        "/specialists": "Для специалистов",
        "/contacts": "Контакты",
        "/privacy": "Privacy Policy — Zumbot",
        "/terms": "Terms of Service — Zumbot",
        "/privacy-ru": "Политика конфиденциальности Zumbot",
        "/terms-ru": "Условия использования Zumbot",
    }

    for path, title in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text


def test_pricing_page_cta_links_open_bot_in_new_tab():
    response = client.get("/pricing")

    assert response.status_code == 200

    # Тарифные CTA + финальный CTA-блок на странице pricing.
    pricing_cta_links = re.findall(r'<a[^>]+href="https://t.me/zumhelper_bot"[^>]*>', response.text)
    assert len(pricing_cta_links) >= 5

    for link in pricing_cta_links:
        assert 'target="_blank"' in link
        assert 'rel="' in link
        assert 'noopener' in link
        assert 'noreferrer' in link

    assert 'https://t.me/zumhelper_bot?start=' not in response.text
    assert 'data-bot-link=' not in response.text

def test_privacy_page_contains_google_calendar_policy_points():
    response = client.get("/privacy")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert "Google API Services User Data Policy" in response.text
    assert "Alexander Bosov" in response.text
    assert "myaccount.google.com/permissions" in response.text
    assert "info@zumbot.ru" in response.text


def test_terms_page_contains_required_clauses():
    response = client.get("/terms")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert "Limitation of Liability" in response.text
    assert "laws of the Russian Federation" in response.text
    assert "laws of Germany" not in response.text
    assert "info@zumbot.ru" in response.text


def test_russian_legal_pages_are_available():
    privacy_response = client.get("/privacy-ru")
    terms_response = client.get("/terms-ru")

    assert privacy_response.status_code == 200
    assert terms_response.status_code == 200
    assert "Политика конфиденциальности Zumbot" in privacy_response.text
    assert "Условия использования Zumbot" in terms_response.text


def test_site_health_returns_ok():
    response = client.get("/site-health")

    assert response.status_code == 200
    assert response.text == "ok"


def test_site_assets_are_served():
    css = client.get("/assets/styles.css")
    js = client.get("/assets/app.js")

    assert css.status_code == 200
    assert "hero" in css.text
    assert js.status_code == 200
    assert "contact-form" in js.text


def test_success_page_contains_expected_text():
    response = client.get("/success")

    assert response.status_code == 200
    assert "Готово" in response.text
    assert "Google Календарь подключён. Вернитесь в Telegram, чтобы продолжить настройку." in response.text
    assert response.text.count("Открыть Telegram") == 1
    assert 'href="https://t.me/zumhelper_bot"' in response.text
    assert "tg://resolve?domain=zumbot_support" not in response.text
    assert "https://t.me/zumbot_support" not in response.text


def test_revoke_access_page_contains_google_permissions_link():
    response = client.get("/revoke-access")

    assert response.status_code == 200
    assert "myaccount.google.com/permissions" in response.text
    assert "Revoke Google Access" in response.text


def test_revoke_access_ru_page_contains_google_permissions_link():
    response = client.get("/revoke-access-ru")

    assert response.status_code == 200
    assert "myaccount.google.com/permissions" in response.text
    assert "Отзыв доступа Google" in response.text


class _DummySession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _DummySessionContext:
    async def __aenter__(self) -> _DummySession:
        return _DummySession()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def test_auth_telegram_consume_sets_cookie_and_can_only_be_used_once(monkeypatch):
    token = "raw-connect-token"
    specialist_id = "44444444-4444-4444-8444-444444444444"
    tg_user_id = 777
    consumed = {"done": False}

    async def _consume_connect_token(_session, raw_token: str):
        assert raw_token == token
        if consumed["done"]:
            return None
        consumed["done"] = True
        return specialist_id, tg_user_id

    monkeypatch.setattr(web_server, "async_session_factory", lambda: _DummySessionContext())
    monkeypatch.setattr(web_server.web_connect, "consume_connect_token", _consume_connect_token)

    first = client.post("/auth/telegram/consume", json={"token": token})

    assert first.status_code == 200
    assert first.json() == {"ok": True}
    assert first.cookies.get(web_server.config.WEB_CONNECT_COOKIE_NAME)
    set_cookie = first.headers.get("set-cookie", "")
    assert f"{web_server.config.WEB_CONNECT_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=Lax" in set_cookie
    assert "Path=/" in set_cookie

    second = client.post("/auth/telegram/consume", json={"token": token})

    assert second.status_code == 400
    assert second.json() == {"ok": False, "error": "expired_or_used"}


def test_auth_telegram_consume_rejects_empty_token():
    response = client.post("/auth/telegram/consume", json={"token": "   "})

    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "token_required"}


def test_connect_page_contains_google_form_and_legal_links():
    response = client.get("/connect")

    assert response.status_code == 200
    assert 'form action="/google/oauth/start"' in response.text
    assert 'href="https://zumbot.ru/privacy-ru"' in response.text
    assert 'href="https://zumbot.ru/terms-ru"' in response.text


def test_connect_status_requires_valid_cookie(monkeypatch):
    monkeypatch.setattr(web_server.web_session, "verify_session_cookie", lambda _: None)

    invalid_response = client.get("/connect/status")
    assert invalid_response.status_code == 200
    assert invalid_response.json() == {"ok": False}

    monkeypatch.setattr(
        web_server.web_session,
        "verify_session_cookie",
        lambda _: ("44444444-4444-4444-8444-444444444444", 777),
    )

    valid_response = client.get("/connect/status")
    assert valid_response.status_code == 200
    assert valid_response.json() == {"ok": True}


def test_public_contact_honeypot_returns_ok_without_sending(monkeypatch):
    called = {"smtp": False}

    def _smtp_stub(**kwargs):
        called["smtp"] = True

    monkeypatch.setattr(web_server, "_send_contact_email_smtp", _smtp_stub)

    response = client.post(
        "/public/contact",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello",
            "hp": "bot-filled",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert called["smtp"] is False


def test_public_contact_returns_smtp_not_configured_and_alerts(monkeypatch):
    alerts: list[dict] = []

    async def _notify_stub(where, exc, context=None, **kwargs):
        alerts.append({"where": where, "exc": exc, "context": context or {}})

    for key in (
        "CONTACT_SMTP_HOST",
        "CONTACT_SMTP_PORT",
        "CONTACT_SMTP_USER",
        "CONTACT_SMTP_PASSWORD",
        "CONTACT_SMTP_FROM",
        "CONTACT_SMTP_TO",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(web_server, "notify_exception", _notify_stub)

    response = client.post(
        "/public/contact",
        json={"name": "Alice", "email": "alice@example.com", "message": "Hello"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "smtp_not_configured"}
    assert len(alerts) == 1
    assert alerts[0]["where"] == "web.contact_form"


def test_public_contact_sends_email(monkeypatch):
    sent: list[dict] = []

    def _smtp_stub(**kwargs):
        sent.append(kwargs)

    monkeypatch.setenv("CONTACT_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CONTACT_SMTP_PORT", "587")
    monkeypatch.setenv("CONTACT_SMTP_USER", "mailer")
    monkeypatch.setenv("CONTACT_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("CONTACT_SMTP_FROM", "from@example.com")
    monkeypatch.setenv("CONTACT_SMTP_TO", "to@example.com")
    monkeypatch.setenv("CONTACT_SMTP_TIMEOUT_SECONDS", "11")
    monkeypatch.setattr(web_server, "_send_contact_email_smtp", _smtp_stub)

    response = client.post(
        "/public/contact",
        json={"name": "Alice", "email": "alice@example.com", "message": "Hello from form"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(sent) == 2

    captured = sent[0]
    assert captured["smtp_host"] == "smtp.example.com"
    assert captured["smtp_port"] == 587
    assert captured["smtp_user"] == "mailer"
    assert captured["smtp_password"] == "secret"
    assert captured["smtp_from"] == "from@example.com"
    assert captured["smtp_to"] == "to@example.com"
    assert captured["smtp_timeout_seconds"] == 11
    assert captured["subject"] == "Zumbot contact form: Alice alice@example.com"
    assert "message:\nHello from form" in captured["body"]
    assert "request_id:" in captured["body"]

    autoreply = sent[1]
    assert autoreply["smtp_to"] == "alice@example.com"
    assert autoreply["reply_to"] == "from@example.com"


def test_public_contact_returns_validation_error_for_invalid_email():
    response = client.post(
        "/public/contact",
        json={"name": "Alice", "email": "bad", "message": "Hello"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": False, "error": "validation_error"}


def test_google_oauth_start_without_cookie_does_not_redirect(monkeypatch):
    monkeypatch.setattr(web_server.web_session, "verify_session_cookie", lambda _: None)

    response = client.post("/google/oauth/start", follow_redirects=False)

    assert response.status_code == 200
    assert "Сессия не найдена" in response.text
    assert "location" not in response.headers


def test_google_oauth_start_with_cookie_redirects_to_auth_url(monkeypatch):
    specialist_id = "44444444-4444-4444-8444-444444444444"
    patched_auth_url = "https://example.test/google-auth"

    class _DummyOauthSession:
        async def commit(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

    class _DummyOauthSessionContext:
        async def __aenter__(self):
            return _DummyOauthSession()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    async def _create_oauth_state(_session, incoming_specialist_id, state_type):
        assert str(incoming_specialist_id) == specialist_id
        assert state_type == web_server.OAuthStateType.google_connect
        return "oauth-state-123"

    monkeypatch.setattr(
        web_server.web_session,
        "verify_session_cookie",
        lambda _: (specialist_id, 777),
    )
    monkeypatch.setattr(web_server, "async_session_factory", lambda: _DummyOauthSessionContext())
    monkeypatch.setattr(web_server, "create_oauth_state", _create_oauth_state)
    monkeypatch.setattr(web_server, "get_auth_url", lambda state: patched_auth_url if state == "oauth-state-123" else "")

    response = client.post("/google/oauth/start", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers.get("location") == patched_auth_url
    assert response.headers.get("cache-control") == "no-store"


class _AnalyticsSession:
    def __init__(self, tariff_plan):
        self._tariff_plan = tariff_plan

    async def get(self, model, _pk):
        if model.__name__ == "SpecialistProfile":
            return type("Profile", (), {"tariff_plan": self._tariff_plan})()
        return None

    async def scalar(self, _stmt):
        return 0


class _AnalyticsSessionContext:
    def __init__(self, tariff_plan):
        self._tariff_plan = tariff_plan

    async def __aenter__(self):
        return _AnalyticsSession(self._tariff_plan)

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_analytics_summary_requires_pro_or_higher(monkeypatch):
    monkeypatch.setattr(
        web_server.web_session,
        "verify_session_cookie",
        lambda _: ("44444444-4444-4444-8444-444444444444", 777),
    )
    monkeypatch.setattr(
        web_server,
        "async_session_factory",
        lambda: _AnalyticsSessionContext("start"),
    )

    response = client.get("/analytics/summary")

    assert response.status_code == 403
    assert response.json() == {"detail": "Аналитика доступна на тарифе Pro и выше."}


def test_analytics_summary_allows_team(monkeypatch):
    monkeypatch.setattr(
        web_server.web_session,
        "verify_session_cookie",
        lambda _: ("44444444-4444-4444-8444-444444444444", 777),
    )
    monkeypatch.setattr(
        web_server,
        "async_session_factory",
        lambda: _AnalyticsSessionContext("team"),
    )

    response = client.get("/analytics/summary")

    assert response.status_code == 200
    assert response.json() == {"total_bookings": 0, "confirmed": 0, "canceled": 0}
