from __future__ import annotations

import pytest

from backend.services import public_specialist_service


class DummySessionCtx:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_get_public_specialist_by_slug_uses_canonical_photo_url_without_double_media(monkeypatch):
    profile_row = {
        "id": "profile-id",
        "specialist_id": "spec-1",
        "public_slug": "slug-1",
        "display_name": "Name",
        "specialization": "Spec",
        "hero_quote": "Quote",
        "contact_telegram": None,
        "contact_whatsapp": None,
        "contact_phone": None,
        "contact_email": None,
        "client_bot_username": "bot",
        "is_published": True,
    }
    media_rows = [
        {
            "media_type": "photo",
            "title": "Hero",
            "sort_order": 0,
            "file_key": "media/media/specialists/spec-1/profile_photo.jpg",
        }
    ]

    class Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return DummyResult([profile_row])
            if self.calls == 2:
                return DummyResult([])
            return DummyResult(media_rows)

    monkeypatch.setattr(public_specialist_service, "async_session_factory", lambda: DummySessionCtx(Session()))

    payload = await public_specialist_service.get_public_specialist_by_slug("slug-1")

    assert payload is not None
    assert payload["profile"]["profile_photo_url"] == "/media/specialists/spec-1/profile_photo.jpg"


@pytest.mark.asyncio
async def test_get_public_specialist_by_slug_keeps_legacy_photo_keys_compatible(monkeypatch):
    profile_row = {
        "id": "profile-id",
        "specialist_id": "spec-1",
        "public_slug": "slug-1",
        "display_name": "Name",
        "specialization": "Spec",
        "hero_quote": "Quote",
        "contact_telegram": None,
        "contact_whatsapp": None,
        "contact_phone": None,
        "contact_email": None,
        "client_bot_username": "bot",
        "is_published": True,
    }
    media_rows = [
        {
            "media_type": "photo",
            "title": "Legacy",
            "sort_order": 0,
            "file_key": "specialists/spec-1/legacy_profile_photo.jpg",
        }
    ]

    class Session:
        def __init__(self):
            self.calls = 0

        async def execute(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return DummyResult([profile_row])
            if self.calls == 2:
                return DummyResult([])
            return DummyResult(media_rows)

    monkeypatch.setattr(public_specialist_service, "async_session_factory", lambda: DummySessionCtx(Session()))

    payload = await public_specialist_service.get_public_specialist_by_slug("slug-1")

    assert payload is not None
    assert payload["profile"]["profile_photo_url"] == "/media/specialists/spec-1/legacy_profile_photo.jpg"
