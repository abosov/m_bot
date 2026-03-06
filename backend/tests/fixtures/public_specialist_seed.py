from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_public_specialist_tsareva_e12(session: AsyncSession) -> None:
    """Seed minimal public specialist example for visual checks in tests."""
    profile_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await session.execute(
        text("DELETE FROM specialist_public_media WHERE profile_id IN (SELECT id FROM specialist_public_profile WHERE public_slug = :slug)"),
        {"slug": "TsarevaE_12"},
    )
    await session.execute(
        text("DELETE FROM specialist_public_block WHERE profile_id IN (SELECT id FROM specialist_public_profile WHERE public_slug = :slug)"),
        {"slug": "TsarevaE_12"},
    )
    await session.execute(
        text("DELETE FROM specialist_public_profile WHERE public_slug = :slug"),
        {"slug": "TsarevaE_12"},
    )

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_profile (
                id, public_slug, display_name, specialization, hero_quote,
                contact_telegram, contact_whatsapp, contact_phone, contact_email,
                client_bot_username, is_published, created_at, updated_at
            ) VALUES (
                :id, :public_slug, :display_name, :specialization, :hero_quote,
                :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                :client_bot_username, :is_published, :created_at, :updated_at
            )
            """
        ),
        {
            "id": profile_id,
            "public_slug": "TsarevaE_12",
            "display_name": "Евгения Царёва",
            "specialization": "Психолог, ЭФТ",
            "hero_quote": "Можно по-другому.",
            "contact_telegram": "evgenia_tsareva",
            "contact_whatsapp": "+79990000000",
            "contact_phone": "+79991112233",
            "contact_email": "info@example.com",
            "client_bot_username": "zumbot_client_bot",
            "is_published": True,
            "created_at": now,
            "updated_at": now,
        },
    )

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_block (id, profile_id, block_type, content, sort_order, updated_at)
            VALUES
              (:about_id, :profile_id, 'about', 'Практикующий психолог. Работаю с тревогой и самооценкой.', 10, :updated_at),
              (:education_id, :profile_id, 'education', 'Психологическое образование и регулярная супервизия.', 20, :updated_at),
              (:services_id, :profile_id, 'services', 'Индивидуальные онлайн-консультации 50 минут.', 30, :updated_at)
            """
        ),
        {
            "about_id": str(uuid.uuid4()),
            "education_id": str(uuid.uuid4()),
            "services_id": str(uuid.uuid4()),
            "profile_id": profile_id,
            "updated_at": now,
        },
    )

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_media (id, profile_id, media_type, title, file_key, sort_order, created_at)
            VALUES (:m1, :profile_id, 'photo', 'Портрет', 'private/demo/tsareva-photo.jpg', 10, :created_at)
            """
        ),
        {
            "m1": str(uuid.uuid4()),
            "profile_id": profile_id,
            "created_at": now,
        },
    )

