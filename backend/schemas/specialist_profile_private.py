from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, field_validator

import config


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


def _normalize_public_return_url(value: str | None) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        raise ValueError("return_url_required")

    public_site_url = (config.PUBLIC_SITE_URL or "").strip().rstrip("/")
    public_site_parts = urlparse(public_site_url)
    if not public_site_parts.scheme or not public_site_parts.netloc:
        raise ValueError("return_url_not_allowed")

    if raw_value.startswith("/"):
        return urljoin(f"{public_site_url}/", raw_value.lstrip("/"))

    parsed_value = urlparse(raw_value)
    if (
        parsed_value.scheme == public_site_parts.scheme
        and parsed_value.netloc == public_site_parts.netloc
    ):
        return raw_value

    raise ValueError("return_url_not_allowed")


class SpecialistSubscriptionPaymentStartRequest(BaseModel):
    tariff_code: str
    return_url: str

    @field_validator("tariff_code", mode="before")
    @classmethod
    def _normalize_tariff_code(cls, value: str | None) -> str:
        normalized = str(value or "").strip().lower()
        if not normalized:
            raise ValueError("tariff_code_required")
        return normalized

    @field_validator("return_url", mode="before")
    @classmethod
    def _normalize_return_url(cls, value: str | None) -> str:
        return _normalize_public_return_url(value)


class SpecialistSubscriptionPaymentStartResponse(BaseModel):
    payment_id: str
    tariff_code: str
    payment_status: str
    requires_redirect: bool = True
    confirmation_url: str
