from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


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


class SpecialistProfilePrivateUpdateRequest(BaseModel):
    first_name: str = Field(default="", max_length=200)
    middle_name: str = Field(default="", max_length=200)
    last_name: str = Field(default="", max_length=200)
    specialization: str = Field(default="", max_length=200)
    hero_quote: str = Field(default="", max_length=200)
    about: str = Field(default="", max_length=8000)
    education: str = Field(default="", max_length=8000)
    services: str = Field(default="", max_length=8000)
    reviews: str = Field(default="", max_length=8000)

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

    @field_validator("specialization")
    @classmethod
    def _validate_specialization(cls, value: str) -> str:
        if value and len(value) > 200:
            raise ValueError("specialization_too_long")
        if not value:
            raise ValueError("specialization_required")
        return value

    @field_validator("hero_quote")
    @classmethod
    def _validate_hero_quote(cls, value: str) -> str:
        if len(value) > 200:
            raise ValueError("hero_quote_too_long")
        return value

    @field_validator("about", "education", "services", "reviews")
    @classmethod
    def _validate_blocks(cls, value: str) -> str:
        if len(value) > 8000:
            raise ValueError("block_too_long")
        return value


class SpecialistProfileMediaItemResponse(BaseModel):
    id: str
    media_type: str
    title: str
    sort_order: int
    created_at: datetime


class SpecialistProfileMediaListResponse(BaseModel):
    items: list[SpecialistProfileMediaItemResponse]


class SpecialistProfileUploadResponse(BaseModel):
    ok: bool = True
