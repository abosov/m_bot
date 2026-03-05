import pytest

from services import web_connect_links


def test_build_profile_edit_page_url_contains_path_and_token(monkeypatch):
    monkeypatch.setattr(web_connect_links, "PUBLIC_SITE_URL", "https://example.test")

    url = web_connect_links.build_profile_edit_page_url("tok123")

    assert url == "https://example.test/profile/edit#token=tok123"


@pytest.mark.asyncio
async def test_create_profile_edit_page_url_uses_connect_token_service(monkeypatch):
    monkeypatch.setattr(web_connect_links, "PUBLIC_SITE_URL", "https://example.test")

    async def _fake_create_connect_token(session, specialist_id, tg_user_id, ttl_minutes=15):
        assert session == "session"
        assert specialist_id == "sp-id"
        assert tg_user_id == 777
        assert ttl_minutes == 20
        return "raw-token"

    monkeypatch.setattr(web_connect_links.web_connect, "create_connect_token", _fake_create_connect_token)

    url = await web_connect_links.create_profile_edit_page_url(
        session="session",
        specialist_id="sp-id",
        tg_user_id=777,
        ttl_minutes=20,
    )

    assert url == "https://example.test/profile/edit#token=raw-token"


@pytest.mark.asyncio
async def test_build_profile_edit_url_for_specialist_uses_hash_token(monkeypatch):
    monkeypatch.setattr(web_connect_links, "PUBLIC_SITE_URL", "https://example.test")

    async def _fake_create_connect_token(session, specialist_id, tg_user_id, ttl_minutes=15):
        assert session == "session"
        assert specialist_id == "sp-id"
        assert tg_user_id == 777
        assert ttl_minutes == 15
        return "raw-token-2"

    monkeypatch.setattr(web_connect_links.web_connect, "create_connect_token", _fake_create_connect_token)

    url = await web_connect_links.build_profile_edit_url_for_specialist(
        session="session",
        specialist_id="sp-id",
        tg_user_id=777,
    )

    assert url == "https://example.test/profile/edit#token=raw-token-2"
    assert "?token=" not in url


def test_build_profile_edit_page_url_raises_when_public_site_url_missing(monkeypatch):
    monkeypatch.setattr(web_connect_links, "PUBLIC_SITE_URL", "")

    with pytest.raises(ValueError):
        web_connect_links.build_profile_edit_page_url("tok123")
