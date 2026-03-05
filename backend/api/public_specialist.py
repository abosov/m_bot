from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from backend.schemas.public_specialist import PublicSpecialistResponse
from services.public_specialist import get_public_specialist_by_slug


router = APIRouter(prefix="/api/public/specialists", tags=["public-specialist"])

_SLUG_RE = re.compile(r"^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$")
_RESERVED_SLUGS = {
    "pricing",
    "privacy",
    "terms",
    "revoke-access",
    "api",
    "static",
    "assets",
}


def _validate_public_slug(slug: str) -> None:
    if slug in _RESERVED_SLUGS:
        raise HTTPException(status_code=400, detail="invalid_slug")

    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(status_code=400, detail="invalid_slug_format")

    try:
        suffix = int(slug.split("_", maxsplit=1)[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="invalid_slug_suffix") from None

    if suffix < 10 or suffix > 30:
        raise HTTPException(status_code=400, detail="invalid_slug_suffix_range")


@router.get("/{public_slug}", response_model=PublicSpecialistResponse)
async def get_public_specialist_profile(public_slug: str) -> PublicSpecialistResponse:
    _validate_public_slug(public_slug)

    data = await get_public_specialist_by_slug(public_slug)
    if data is None:
        raise HTTPException(status_code=404, detail="not_found")

    media_public: list[dict[str, object]] = []
    for item in data.get("media", []):
        media_public.append(
            {
                "media_type": item.get("media_type"),
                "title": item.get("title"),
                "sort_order": item.get("sort_order"),
                "url": None,
            }
        )

    payload = {
        "profile": data.get("profile", {}),
        "blocks": data.get("blocks", []),
        "media": media_public,
    }
    return PublicSpecialistResponse.model_validate(payload)
