from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.database.models import (
    Base,
    PublicSpecialistBlock,
    PublicSpecialistMedia,
    PublicSpecialistProfile,
    PublicSpecialistReview,
)


def test_public_specialist_models_insert_and_select_roundtrip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    profile_id = uuid.uuid4()

    with Session(engine) as session:
        profile = PublicSpecialistProfile(
            id=profile_id,
            public_slug="TsarevaE_12",
            display_name="Евгения Царёва",
            specialization="Психолог",
            hero_quote="Можно по-другому.",
            contact_telegram="evgenia_tsareva",
            contact_whatsapp="+79990000000",
            contact_phone="+79991112233",
            contact_email="info@example.com",
            client_bot_username="zumbot_client_bot",
            is_published=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        profile.blocks.append(
            PublicSpecialistBlock(
                id=uuid.uuid4(),
                block_type="about",
                content="О себе",
                sort_order=10,
                updated_at=datetime.now(timezone.utc),
            )
        )
        profile.reviews.append(
            PublicSpecialistReview(
                id=uuid.uuid4(),
                author_name="Клиент",
                rating=5,
                content="Отзыв",
                sort_order=10,
                created_at=datetime.now(timezone.utc),
            )
        )
        profile.media.append(
            PublicSpecialistMedia(
                id=uuid.uuid4(),
                media_type="photo",
                title="Фото",
                file_key="private/media/key.jpg",
                sort_order=10,
                created_at=datetime.now(timezone.utc),
            )
        )

        session.add(profile)
        session.commit()

        loaded_profile = session.scalar(
            select(PublicSpecialistProfile).where(PublicSpecialistProfile.id == profile_id)
        )

        assert loaded_profile is not None
        assert loaded_profile.public_slug == "TsarevaE_12"
        assert len(loaded_profile.blocks) == 1
        assert len(loaded_profile.reviews) == 1
        assert len(loaded_profile.media) == 1
