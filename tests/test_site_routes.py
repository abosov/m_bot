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


def test_privacy_page_contains_google_calendar_policy_points():
    response = client.get("/privacy")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert "Google API Services User Data Policy" in response.text
    assert "Alexander Bosov" in response.text
    assert "myaccount.google.com/permissions" in response.text
    assert "abosov@gmail.com" in response.text


def test_terms_page_contains_required_clauses():
    response = client.get("/terms")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert "Limitation of Liability" in response.text
    assert "abosov@gmail.com" in response.text


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
    assert "Zumbot landing page loaded" in js.text


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
