from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text

from database import async_session_factory


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


async def get_public_specialist_by_slug(public_slug: str) -> dict[str, Any] | None:
    async with async_session_factory() as session:
        profile_row = (
            await session.execute(
                text(
                    """
                    SELECT
                        id,
                        public_slug,
                        display_name,
                        specialization,
                        hero_quote,
                        contact_telegram,
                        contact_whatsapp,
                        contact_phone,
                        contact_email,
                        client_bot_username,
                        is_published
                    FROM specialist_public_profile
                    WHERE public_slug = :public_slug
                    """
                ),
                {"public_slug": public_slug},
            )
        ).mappings().first()

        if profile_row is None:
            return None

        profile_id = profile_row["id"]

        block_rows = (
            await session.execute(
                text(
                    """
                    SELECT block_type, content, sort_order, updated_at
                    FROM specialist_public_block
                    WHERE profile_id = :profile_id
                    ORDER BY sort_order ASC, block_type ASC
                    """
                ),
                {"profile_id": profile_id},
            )
        ).mappings().all()

        media_rows = (
            await session.execute(
                text(
                    """
                    SELECT media_type, title, sort_order
                    FROM specialist_public_media
                    WHERE profile_id = :profile_id
                    ORDER BY sort_order ASC, created_at ASC
                    """
                ),
                {"profile_id": profile_id},
            )
        ).mappings().all()

        return {
            "profile": {
                "id": str(profile_row["id"]),
                "public_slug": profile_row["public_slug"],
                "display_name": profile_row["display_name"],
                "specialization": profile_row["specialization"],
                "hero_quote": profile_row["hero_quote"],
                "contacts": {
                    "telegram": profile_row["contact_telegram"],
                    "whatsapp": profile_row["contact_whatsapp"],
                    "phone": profile_row["contact_phone"],
                    "email": profile_row["contact_email"],
                },
                "client_bot_username": profile_row["client_bot_username"],
                "is_published": bool(profile_row["is_published"]),
            },
            "blocks": [
                {
                    "block_type": row["block_type"],
                    "content": row["content"],
                    "sort_order": row["sort_order"],
                    "updated_at": _iso(row["updated_at"]),
                }
                for row in block_rows
            ],
            "media": [
                {
                    "media_type": row["media_type"],
                    "title": row["title"],
                    "sort_order": row["sort_order"],
                    "url": None,
                }
                for row in media_rows
            ],
            # Reviews table is not part of specialist_public_* storage yet.
            "reviews": [],
        }
