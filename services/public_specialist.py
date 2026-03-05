from __future__ import annotations

from typing import Any

from sqlalchemy import select

from database import (
    SpecialistPublicBlock,
    SpecialistPublicMedia,
    SpecialistPublicProfile,
    async_session_factory,
)


async def get_public_specialist_by_slug(public_slug: str) -> dict[str, Any] | None:
    """Return aggregated public specialist profile by slug, published only."""
    async with async_session_factory() as session:
        profile = (
            await session.execute(
                select(SpecialistPublicProfile).where(
                    SpecialistPublicProfile.public_slug == public_slug,
                    SpecialistPublicProfile.is_published.is_(True),
                )
            )
        ).scalar_one_or_none()

        if profile is None:
            return None

        blocks = (
            await session.execute(
                select(SpecialistPublicBlock)
                .where(SpecialistPublicBlock.profile_id == profile.id)
                .order_by(
                    SpecialistPublicBlock.sort_order.asc(),
                    SpecialistPublicBlock.block_type.asc(),
                )
            )
        ).scalars().all()

        media = (
            await session.execute(
                select(SpecialistPublicMedia)
                .where(SpecialistPublicMedia.profile_id == profile.id)
                .order_by(
                    SpecialistPublicMedia.sort_order.asc(),
                    SpecialistPublicMedia.created_at.asc(),
                )
            )
        ).scalars().all()

        return {
            "profile": {
                "id": str(profile.id),
                "public_slug": profile.public_slug,
                "display_name": profile.display_name,
                "specialization": profile.specialization,
                "hero_quote": profile.hero_quote,
                "contacts": {
                    "telegram": profile.contact_telegram,
                    "whatsapp": profile.contact_whatsapp,
                    "phone": profile.contact_phone,
                    "email": profile.contact_email,
                },
                "client_bot_username": profile.client_bot_username,
            },
            "blocks": [
                {
                    "block_type": block.block_type,
                    "content": block.content,
                    "sort_order": block.sort_order,
                    "updated_at": block.updated_at.isoformat() if block.updated_at else None,
                }
                for block in blocks
            ],
            "media": [
                {
                    "media_type": item.media_type,
                    "file_key": item.file_key,
                    "title": item.title,
                    "sort_order": item.sort_order,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in media
            ],
        }
