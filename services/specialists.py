from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Specialist, SpecialistAuthTelegram, SpecialistProfile, SpecialistStatus
from services.specialist_defaults import DEFAULT_TIMEZONE


async def ensure_specialist_with_profile_for_tg_user(
    session: AsyncSession,
    tg_user_id: int,
    tg_username: Optional[str],
    tg_first_name: Optional[str],
    tg_last_name: Optional[str] = None,
) -> Specialist:
    """Ensure Specialist + auth + profile exist for telegram user before onboarding completion."""

    auth = (
        await session.execute(
            select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
        )
    ).scalar_one_or_none()

    specialist: Specialist | None
    if auth is None:
        specialist = Specialist(status=SpecialistStatus.onboarding)
        session.add(specialist)
        await session.flush()
        auth = SpecialistAuthTelegram(
            specialist_id=specialist.specialist_id,
            tg_user_id=tg_user_id,
            tg_username=tg_username,
            tg_first_name=tg_first_name,
            tg_last_name=tg_last_name,
        )
        session.add(auth)
    else:
        specialist = await session.get(Specialist, auth.specialist_id)
        if specialist is None:
            specialist = Specialist(specialist_id=auth.specialist_id, status=SpecialistStatus.onboarding)
            session.add(specialist)
        auth.tg_username = tg_username
        auth.tg_first_name = tg_first_name
        auth.tg_last_name = tg_last_name

    profile = await session.get(SpecialistProfile, specialist.specialist_id)
    if profile is None:
        public_name = (tg_username or tg_first_name or "Специалист").strip() or "Специалист"
        profile = SpecialistProfile(
            specialist_id=specialist.specialist_id,
            public_name=public_name,
            owner_tg_user_id=tg_user_id,
            owner_tg_username=tg_username,
            specialist_timezone=DEFAULT_TIMEZONE,
            onboarding_completed=False,
        )
        session.add(profile)

    await session.commit()
    return specialist
