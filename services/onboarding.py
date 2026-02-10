import uuid

from sqlalchemy import select

from database import (
    Specialist,
    SpecialistProfile,
    SpecialistCalendarSettings,
    SpecialistStatus,
    TelegramBot,
    TelegramBotStatus,
    async_session_factory,
)


async def is_specialist_ready(specialist_id: uuid.UUID) -> bool:
    """Specialist is ready when profile, active personal bot, calendar selection and successful smoke-test exist."""
    async with async_session_factory() as session:
        profile_exists = (
            await session.execute(
                select(SpecialistProfile.specialist_id).where(
                    SpecialistProfile.specialist_id == specialist_id,
                    SpecialistProfile.public_name.is_not(None),
                    SpecialistProfile.public_name != "",
                )
            )
        ).scalar_one_or_none()

        active_bot_exists = (
            await session.execute(
                select(TelegramBot.telegram_bot_id).where(
                    TelegramBot.specialist_id == specialist_id,
                    TelegramBot.status == TelegramBotStatus.active,
                )
            )
        ).scalar_one_or_none()

        calendar_ready = (
            await session.execute(
                select(SpecialistCalendarSettings.specialist_id).where(
                    SpecialistCalendarSettings.specialist_id == specialist_id,
                    SpecialistCalendarSettings.calendar_id.is_not(None),
                    SpecialistCalendarSettings.calendar_id != "",
                    SpecialistCalendarSettings.last_smoke_test_status == "ok",
                )
            )
        ).scalar_one_or_none()

    return bool(profile_exists and active_bot_exists and calendar_ready)


async def finalize_specialist_if_ready(specialist_id: uuid.UUID) -> bool:
    """Move specialist status onboarding -> active when onboarding minimum is complete."""
    if not await is_specialist_ready(specialist_id):
        return False

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_id)
        if not specialist:
            return False

        if specialist.status == SpecialistStatus.active:
            return False

        if specialist.status != SpecialistStatus.onboarding:
            return False

        specialist.status = SpecialistStatus.active
        await session.commit()
        return True
