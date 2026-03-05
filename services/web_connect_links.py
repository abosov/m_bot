from __future__ import annotations

from config import PUBLIC_SITE_URL
from services import web_connect


def _resolve_public_site_base(public_site_url: str | None = None) -> str:
    base_url = (public_site_url or PUBLIC_SITE_URL or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("public_site_url_missing")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ValueError("public_site_url_invalid")
    return base_url


def build_connect_page_url(raw_token: str, *, public_site_url: str | None = None) -> str:
    base_url = _resolve_public_site_base(public_site_url)
    return f"{base_url}/connect#token={raw_token}"


def build_profile_edit_page_url(raw_token: str, *, public_site_url: str | None = None) -> str:
    base_url = _resolve_public_site_base(public_site_url)
    return f"{base_url}/profile/edit#token={raw_token}"


async def build_profile_edit_url_for_specialist(*, session, specialist_id, tg_user_id: int, ttl_minutes: int = 15) -> str:
    raw_token = await web_connect.create_connect_token(
        session,
        specialist_id,
        tg_user_id,
        ttl_minutes=ttl_minutes,
    )
    return build_profile_edit_page_url(raw_token)


async def create_profile_edit_page_url(*, session, specialist_id, tg_user_id: int, ttl_minutes: int = 15) -> str:
    return await build_profile_edit_url_for_specialist(
        session=session,
        specialist_id=specialist_id,
        tg_user_id=tg_user_id,
        ttl_minutes=ttl_minutes,
    )
