from fastapi.testclient import TestClient

import web_server


client = TestClient(web_server.app)


def test_site_index_returns_landing():
    response = client.get("/")

    assert response.status_code == 200
    assert "Zumbot — умный бот для записи клиентов" in response.text


def test_site_pages_are_available():
    expected = {
        "/features": "Возможности Zumbot",
        "/pricing": "Тарифы",
        "/specialists": "Для специалистов",
        "/contacts": "Контакты",
        "/privacy": "Политика конфиденциальности",
        "/terms": "Пользовательское соглашение",
    }

    for path, title in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text


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
