from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PublicSpecialistContacts(BaseModel):
    telegram: str | None = None
    whatsapp: str | None = None
    phone: str | None = None
    email: str | None = None


class PublicSpecialistProfile(BaseModel):
    id: str
    public_slug: str
    display_name: str
    specialization: str
    hero_quote: str | None = None
    profile_photo_url: str | None = None
    contacts: PublicSpecialistContacts
    client_bot_username: str


class PublicSpecialistBlock(BaseModel):
    block_type: str
    content: str
    sort_order: int
    updated_at: str | None = None


class PublicSpecialistMedia(BaseModel):
    media_type: Literal["photo", "document"]
    title: str | None = None
    sort_order: int
    url: str | None = None




class PublicSpecialistReview(BaseModel):
    author_name: str | None = None
    rating: int | None = None
    content: str
    sort_order: int
    created_at: str | None = None


class PublicSpecialistResponse(BaseModel):
    profile: PublicSpecialistProfile
    blocks: list[PublicSpecialistBlock]
    media: list[PublicSpecialistMedia]
    reviews: list[PublicSpecialistReview]
