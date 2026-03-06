import re

from fastapi.testclient import TestClient

import config
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
        "/success": "Готово — Zumbot",
        "/profile/edit": "Профиль специалиста — Zumbot",
    }

    for path, title in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert title in response.text


def test_pricing_page_cta_links_open_bot_in_new_tab():
    response = client.get("/pricing")

    assert response.status_code == 200

    # Разрешённые ссылки для Telegram CTA.
    allowed_bot_links = {
        "https://t.me/zumhelper_bot?start=start",
        "https://t.me/zumhelper_bot?start=pro",
        "https://t.me/zumhelper_bot?start=team",
    }

    pricing_cta_links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>', response.text)
    telegram_links = [href for href in pricing_cta_links if href.startswith("https://t.me/zumhelper_bot")]

    assert telegram_links, "Expected Telegram links on /pricing"
    assert "https://t.me/zumhelper_bot" not in telegram_links
    assert set(telegram_links).issubset(allowed_bot_links)

    # На карточке Team CTA должен вести в контакты сайта, а не в Telegram.
    assert 'href="/contacts" target="_blank" rel="noopener noreferrer">Связаться с нами</a>' in response.text

    links_with_tg = re.findall(r'<a[^>]+href="https://t.me/zumhelper_bot[^\"]*"[^>]*>', response.text)
    for link in links_with_tg:
        assert 'target="_blank"' in link
        assert 'rel="' in link
        assert 'noopener' in link
        assert 'noreferrer' in link

    assert 'href="https://t.me/zumhelper_bot"' not in response.text
    assert "window.location" not in response.text

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




def test_public_slug_route_returns_full_public_specialist_page_markup():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Профиль специалиста — Zumbot" in response.text
    assert 'id="public-specialist-loading"' in response.text
    assert 'id="public-specialist-not-found"' in response.text
    assert 'id="specialist-page"' in response.text
    assert 'id="specialist-sticky-header"' in response.text
    assert 'aria-label="Навигация по разделам специалиста"' in response.text
    assert ">О себе<" in response.text
    assert ">Образование<" in response.text
    assert ">Документы<" in response.text
    assert ">Услуги и цены<" in response.text
    assert ">Отзывы<" in response.text
    assert ">Записаться<" in response.text
    assert "const apiBaseUrl = " in response.text
    assert f'const apiBaseUrl = "{config.BASE_URL}";' in response.text
    assert "const publicProfileApiUrl = `${apiBaseUrl.replace(/\\/$/, '')}/api/public/specialists/${encodeURIComponent(slug)}`;" in response.text
    assert 'const slug = "TsarevaE_12";' in response.text
    assert "bootstrap().catch(showNotFound);" in response.text
    assert 'id="specialist-loading"' not in response.text
    assert 'id="specialist-not-found"' not in response.text
    assert 'id="specialist-content"' not in response.text



def test_public_slug_route_logs_render_event_without_personal_data(caplog):
    with caplog.at_level("INFO", logger="web_server"):
        response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "event=public_slug_route_rendered" in caplog.text
    assert "slug=TsarevaE_12" in caplog.text
    assert "route_name=specialist_profile_page" in caplog.text
    assert f"api_base_url={config.BASE_URL}" in caplog.text
    assert "tg_user_id=" not in caplog.text
    assert "token=" not in caplog.text

def test_public_slug_route_keeps_not_found_container_markup():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert 'id="public-specialist-not-found"' in response.text
    assert "Профиль не найден" in response.text


def test_public_slug_route_has_failsafe_handlers_for_runtime_errors():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "window.addEventListener('error', showNotFound);" in response.text
    assert "window.addEventListener('unhandledrejection', showNotFound);" in response.text
    assert "bootstrap().catch(showNotFound);" in response.text


def test_public_slug_route_hides_loading_when_api_returns_non_ok_status():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "if (!response.ok) {" in response.text
    assert "throw new Error(String(response.status));" in response.text
    assert "loadingEl.style.display = 'none';" in response.text
    assert "notFoundEl.classList.remove('specialist-hidden');" in response.text




def test_public_slug_route_hero_places_photo_left_and_quote_right():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert 'id="public-specialist-hero-grid"' in response.text
    assert 'class="section-card specialist-hero hero-grid specialist-card"' in response.text
    assert 'class="specialist-hero__photo-wrap profile-photo"' in response.text
    assert "quoteEl.classList.remove('specialist-hidden');" in response.text
    assert "quoteEl.classList.add('specialist-hidden');" in response.text


def test_public_slug_route_reviews_rendering_uses_blocks_not_reviews_array():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "const reviewsBlock = Array.isArray(blocks)" in response.text
    assert "renderReviews(blocksSource);" in response.text
    assert "renderReviews(payload?.reviews);" not in response.text


def test_public_slug_route_documents_rendering_uses_document_media_only():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "(item && item.media_type)" in response.text
    assert "=== 'document'" in response.text
    assert "if (/^https?:\\/\\//i.test(item.url))" in response.text
    assert "Скоро будет доступно скачивание" in response.text




def test_public_slug_route_runtime_bridge_avoids_optional_chaining_and_nullish_coalescing():
    response = client.get("/TsarevaE_12")

    assert response.status_code == 200
    assert "?." not in response.text
    assert "??" not in response.text
    assert f'const apiBaseUrl = "{config.BASE_URL}";' in response.text
    assert "bootstrap().catch(showNotFound);" in response.text

def test_public_slug_route_keeps_reserved_paths_on_existing_pages():
    response = client.get("/pricing")

    assert response.status_code == 200
    assert "Тарифы" in response.text


def test_invalid_single_segment_path_is_not_hijacked_by_specialist_page_router():
    response = client.get("/invalid-slug")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_site_assets_are_served():
    css = client.get("/assets/styles.css")
    js = client.get("/assets/app.js")

    assert css.status_code == 200
    assert "hero" in css.text
    assert js.status_code == 200
    assert "contact-form" in js.text


def test_success_page_uses_site_chrome_and_contains_expected_text():
    response = client.get("/success")

    assert response.status_code == 200
    assert "Готово — Zumbot" in response.text
    assert 'class="site-header"' in response.text
    assert 'class="site-footer"' in response.text
    assert "Google Календарь подключён. Вернитесь в Telegram, чтобы продолжить настройку." in response.text
    assert response.text.count("Открыть Telegram") == 1
    assert 'href="https://t.me/zumhelper_bot"' in response.text
    assert 'target="_blank"' in response.text
    assert 'rel="noopener noreferrer"' in response.text
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




def test_old_telegram_link_token_is_single_use_and_then_returns_expired_or_used(monkeypatch):
    old_token = "old-message-token"
    specialist_id = "44444444-4444-4444-8444-444444444444"
    tg_user_id = 777
    consumed = {"done": False}

    async def _consume_connect_token(_session, raw_token: str):
        assert raw_token == old_token
        if consumed["done"]:
            return None
        consumed["done"] = True
        return specialist_id, tg_user_id

    monkeypatch.setattr(web_server, "async_session_factory", lambda: _DummySessionContext())
    monkeypatch.setattr(web_server.web_connect, "consume_connect_token", _consume_connect_token)

    first = client.post("/auth/telegram/consume", json={"token": old_token})
    second = client.post("/auth/telegram/consume", json={"token": old_token})

    assert first.status_code == 200
    assert first.json() == {"ok": True}
    assert second.status_code == 400
    assert second.json() == {"ok": False, "error": "expired_or_used"}


def test_auth_telegram_consume_rejects_empty_token():
    response = client.post("/auth/telegram/consume", json={"token": "   "})

    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "token_required"}




def test_profile_edit_page_contains_auth_status_and_working_form_sections():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "Профиль специалиста" in response.text
    assert "✅ Авторизовано" in response.text
    assert 'id="auth-error"' in response.text
    assert "Публичная страница" in response.text
    assert "Опубликовать" in response.text
    assert "Копировать" in response.text
    assert "Ссылка появится после создания slug" not in response.text
    assert "Ссылка появится после сохранения основной информации." in response.text
    assert 'id="copy-public-link" type="button" class="btn-secondary" disabled' in response.text
    assert "Основное" in response.text
    assert "Цитата" in response.text
    assert '<div class="subblock-secondary">' not in response.text
    assert 'id="save-quote"' in response.text
    assert 'id="status-quote"' in response.text
    assert response.text.index("Основное") < response.text.index("Цитата")
    assert response.text.index("Сначала сохраните основную информацию, чтобы создать ссылку профиля.") < response.text.index("Цитата")
    assert "Сначала сохраните основную информацию, чтобы создать ссылку профиля." in response.text
    assert "secondary-lock-hint" in response.text
    assert "setSecondarySectionsLocked" in response.text
    assert "save-main" in response.text
    assert "О себе" in response.text
    assert "Образование" in response.text
    assert "Документы" in response.text
    assert "Услуги и цены" in response.text
    assert "Отзывы" in response.text
    assert "Загрузить фото" in response.text
    assert "Загрузить документы" in response.text
    assert response.text.index("Основное") < response.text.index("Фото") < response.text.index("Цитата") < response.text.index("О себе") < response.text.index("Образование") < response.text.index("Документы") < response.text.index("Услуги и цены") < response.text.index("Отзывы")



def test_profile_edit_public_state_rendering_handles_no_slug_draft_and_published_states():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "if (!publicUrl)" in response.text
    assert "linkEl.removeAttribute('href')" in response.text
    assert "copyBtn.disabled = true" in response.text
    assert "copyBtn.disabled = false" in response.text
    assert "publishBtn.disabled = true" in response.text
    assert "publishBtn.disabled = false" in response.text
    assert "statusBadge.textContent = isPublished ? 'Опубликовано' : 'Черновик'" in response.text


def test_profile_edit_save_main_reloads_profile_meta_and_unlocks_secondary_sections():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "currentProfileMeta" in response.text
    assert "async function reloadProfileMeta()" in response.text
    assert "await reloadProfileMeta();" in response.text
    assert "setCurrentProfileMeta(data);" in response.text
    assert "setSecondarySectionsLocked(!hasProfileSlug())" in response.text


def test_profile_edit_quote_is_secondary_block_and_saved_separately():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "'save-quote', 'save-about', 'save-education', 'save-services', 'save-reviews', 'upload-photo', 'upload-documents'" in response.text
    assert "document.getElementById('save-quote').addEventListener('click'" in response.text
    assert "saveBlock('save-quote', 'status-quote', {" in response.text
    assert "hero_quote: fields.hero_quote.value" in response.text
    assert "saveBlock('save-main', 'status-main', {" in response.text
    assert "specialization: fields.specialization.value," in response.text
    assert "specialization: fields.specialization.value,\n            hero_quote: fields.hero_quote.value," not in response.text






def test_profile_edit_old_message_flow_shows_return_to_bot_guidance():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "Ссылка устарела или уже была использована. Вернитесь в бот и запросите новую." in response.text
    assert "Ссылка для входа не найдена. Откройте страницу из бота." in response.text


def test_profile_edit_auth_error_messages_are_explicit_for_missing_and_expired_tokens():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "Ссылка для входа не найдена. Откройте страницу из бота." in response.text
    assert "Ссылка устарела или уже была использована. Вернитесь в бот и запросите новую." in response.text
    assert "resolveAuthErrorText({ tokenPresent, consumeError })" in response.text
    assert "consumeError === 'expired_or_used'" in response.text


def test_profile_edit_uses_existing_session_when_token_consume_failed():
    response = client.get("/profile/edit")

    assert response.status_code == 200
    assert "if (!authorized) {" in response.text
    assert "authorized = await checkSession();" in response.text
    assert "if (consumeResult.ok) clearHash();" in response.text
    assert "error.textContent = `❌ ${resolveAuthErrorText({ tokenPresent, consumeError })}`;" in response.text

def test_connect_page_contains_google_form_and_legal_links():
    response = client.get("/connect")

    assert response.status_code == 200
    assert 'form action="/google/oauth/start"' in response.text
    assert 'href="/terms-ru" target="_blank" rel="noopener"' in response.text
    assert 'href="/privacy-ru" target="_blank" rel="noopener"' in response.text
    assert "Для работы записи клиентов необходимо подключить ваш Google Календарь." in response.text
    assert "Zumbot получит доступ только к выбранному календарю" in response.text
    assert "показывать доступные слоты для записи" in response.text
    assert "создавать события при бронировании" in response.text
    assert "отменять события при отмене записи" in response.text
    assert "Мы не получаем доступ к вашей почте или другим данным Google." in response.text
    assert "Авторизация откроется в стандартной странице Google (не во встроенном iframe)." in response.text
    assert "Продолжая, вы подтверждаете согласие" in response.text
    assert "Нажимая кнопку оплаты" not in response.text


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
