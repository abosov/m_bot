from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


def _trim(value: str) -> str:
    return value.strip()


class SpecialistProfilePrivateResponse(BaseModel):
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    specialization: str = ""
    hero_quote: str = ""
    about: str = ""
    education: str = ""
    services: str = ""
    reviews: str = ""
    public_slug: str | None = None
    is_published: bool = False


class SpecialistProfilePrivateUpdateRequest(BaseModel):
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    specialization: str = ""
    hero_quote: str = ""
    about: str = ""
    education: str = ""
    services: str = ""
    reviews: str = ""

    @field_validator(
        "first_name",
        "middle_name",
        "last_name",
        "specialization",
        "hero_quote",
        "about",
        "education",
        "services",
        "reviews",
        mode="before",
    )
    @classmethod
    def _normalize_string(cls, value: str | None) -> str:
        if value is None:
            return ""
        return _trim(str(value))


class SpecialistProfileMediaItemResponse(BaseModel):
    id: str
    media_type: str
    file_key: str | None = None
    title: str
    sort_order: int
    created_at: datetime


class SpecialistProfileMediaListResponse(BaseModel):
    items: list[SpecialistProfileMediaItemResponse]


class SpecialistProfileUploadResponse(BaseModel):
    ok: bool = True


class SpecialistProfilePublishResponse(BaseModel):
    ok: bool = True
    is_published: bool
