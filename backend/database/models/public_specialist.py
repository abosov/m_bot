from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PublicSpecialistProfile(Base):
    __tablename__ = "public_specialist_profile"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    public_slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    specialization: Mapped[str] = mapped_column(Text, nullable=False)
    hero_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_telegram: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_whatsapp: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_bot_username: Mapped[str] = mapped_column(Text, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    blocks: Mapped[list[PublicSpecialistBlock]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list[PublicSpecialistReview]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    media: Mapped[list[PublicSpecialistMedia]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class PublicSpecialistBlock(Base):
    __tablename__ = "public_specialist_block"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public_specialist_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    block_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    profile: Mapped[PublicSpecialistProfile] = relationship(back_populates="blocks")


class PublicSpecialistReview(Base):
    __tablename__ = "public_specialist_review"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public_specialist_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    profile: Mapped[PublicSpecialistProfile] = relationship(back_populates="reviews")


class PublicSpecialistMedia(Base):
    __tablename__ = "public_specialist_media"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("public_specialist_profile.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    profile: Mapped[PublicSpecialistProfile] = relationship(back_populates="media")
