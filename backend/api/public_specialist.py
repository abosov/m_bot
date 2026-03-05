from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from backend.services.public_specialist_service import get_public_specialist_by_slug


router = APIRouter(prefix="/api/public/specialists", tags=["public-specialist"])

_SLUG_RE = re.compile(r"^[A-Za-z]+[A-Za-z]_[1-9][0-9]$")
_RESERVED_PATHS = {
    "pricing",
    "privacy",
    "terms",
    "revoke-access",
    "api",
    "static",
    "assets",
}

_PUBLIC_PROFILE_FIELDS = {
    "id",
    "specialist_id",
    "public_slug",
    "display_name",
    "specialization",
    "hero_quote",
    "contact_telegram",
    "contact_whatsapp",
    "contact_phone",
    "contact_email",
    "client_bot_username",
    "is_published",
    "created_at",
    "updated_at",
}


def _is_valid_slug(slug: str) -> bool:
    if slug in _RESERVED_PATHS:
        return False
    if not _SLUG_RE.fullmatch(slug):
        return False

    try:
        suffix = int(slug.split("_", maxsplit=1)[1])
    except (IndexError, ValueError):
        return False

    return 10 <= suffix <= 30


@router.get("/{slug}")
async def get_public_specialist_profile(slug: str) -> dict:
    if not _is_valid_slug(slug):
        raise HTTPException(status_code=400, detail="invalid_slug")

    data = await get_public_specialist_by_slug(slug)
    if data is None:
        raise HTTPException(status_code=404, detail="not_found")

    profile = data.get("profile") or {}
    if not profile.get("is_published", False):
        raise HTTPException(status_code=404, detail="not_found")

    safe_profile = {k: v for k, v in profile.items() if k in _PUBLIC_PROFILE_FIELDS}

    return {
        "profile": safe_profile,
        "blocks": data.get("blocks", []),
        "media": data.get("media", []),
        "reviews": data.get("reviews", []),
    }
