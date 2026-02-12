import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import Specialist, SpecialistAuthTelegram, SpecialistProfile, TelegramBot, TelegramBotStatus, async_session_factory

logger = logging.getLogger(__name__)


async def get_specialist_by_tg_user_id(tg_user_id: int) -> Optional[Specialist]:
    async with async_session_factory() as session:
        auth = (
            await session.execute(
                select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()
        if auth is None:
            return None
        return await session.get(Specialist, auth.specialist_id)


async def get_specialist_by_owner_tg_user_id(owner_tg_user_id: int) -> Optional[Specialist]:
    async with async_session_factory() as session:
        profile = (
            await session.execute(
                select(SpecialistProfile).where(SpecialistProfile.owner_tg_user_id == owner_tg_user_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            return None
        return await session.get(Specialist, profile.specialist_id)


async def get_specialist_by_personal_bot(bot_username: str) -> Optional[Specialist]:
    normalized = (bot_username or "").strip().lstrip("@")
    if not normalized:
        return None

    async with async_session_factory() as session:
        bot = (
            await session.execute(
                select(TelegramBot)
                .where(
                    TelegramBot.bot_username == normalized,
                    TelegramBot.status == TelegramBotStatus.active,
                )
                .order_by(TelegramBot.updated_at.desc())
            )
        ).scalars().first()
        if bot is None or bot.specialist_id is None:
            return None

        specialist_stmt = (
            select(Specialist)
            .options(selectinload(Specialist.telegram_bots))
            .where(Specialist.specialist_id == bot.specialist_id)
        )
        return (await session.execute(specialist_stmt)).scalar_one_or_none()


async def set_master_onboarding_completed(specialist_id: UUID, completed_at: datetime | None = None) -> None:
    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_id)
        if specialist is None:
            logger.warning("set_master_onboarding_completed: specialist not found specialist_id=%s", specialist_id)
            return
        specialist.onboarding_master_completed_at = completed_at or datetime.now(timezone.utc)
        await session.commit()


async def set_personal_onboarding_completed(specialist_id: UUID, completed_at: datetime | None = None) -> None:
    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_id)
        if specialist is None:
            logger.warning("set_personal_onboarding_completed: specialist not found specialist_id=%s", specialist_id)
            return
        specialist.onboarding_personal_completed_at = completed_at or datetime.now(timezone.utc)
        await session.commit()
