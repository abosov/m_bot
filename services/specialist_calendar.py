import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy import select

from database import (
    CalendarSyncState,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    SpecialistProfile,
    TelegramBot,
    TelegramBotStatus,
    async_session_factory,
)
from services.google_calendar import (
    create_and_cleanup_test_event,
    ensure_calendar_access,
    get_calendar,
)
from services.telegram.bot_factory import get_personal_bot

logger = logging.getLogger(__name__)


async def _notify_specialist_integration_failed(specialist_id: uuid.UUID, error_text: str | None = None) -> None:
    try:
        async with async_session_factory() as session:
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None or profile.owner_tg_user_id is None:
                return

            bot_stmt = (
                select(TelegramBot)
                .where(TelegramBot.specialist_id == specialist_id)
                .where(TelegramBot.status == TelegramBotStatus.active)
                .order_by(TelegramBot.created_at.desc())
                .limit(1)
            )
            bot_row = (await session.execute(bot_stmt)).scalar_one_or_none()
            if bot_row is None:
                return

        personal_bot = await get_personal_bot(bot_row)
        suffix = f"\nПричина: {error_text}" if error_text else ""
        await personal_bot.send_message(
            chat_id=profile.owner_tg_user_id,
            text=(
                "⚠️ Не удалось завершить проверку интеграции календаря.\n"
                "Календарь сохранён, но подключение работает с ошибкой. "
                "Проверьте доступ Google Calendar и попробуйте снова."
                f"{suffix}"
            ),
        )
    except Exception:
        logger.exception(
            "set_specialist_calendar failed to notify specialist specialist_id=%s",
            specialist_id,
        )


async def set_specialist_calendar(specialist_id: uuid.UUID, calendar_id: str) -> str:
    """Bind specialist to a Google Calendar and run integration smoke test.

    Returns:
        "ok" when access check + smoke test passed, otherwise "failed".
    """

    normalized_calendar_id = (calendar_id or "").strip()
    if not normalized_calendar_id:
        return "failed"

    smoke_status = "failed"
    smoke_error: str | None = None
    calendar_tz = "UTC"
    calendar_summary: str | None = None

    try:
        await ensure_calendar_access(specialist_id, normalized_calendar_id)
        calendar_payload = await get_calendar(specialist_id, normalized_calendar_id)
        calendar_tz = (calendar_payload.get("timeZone") or "UTC").strip() or "UTC"
        calendar_summary = calendar_payload.get("summary")

        async with async_session_factory() as session:
            profile = await session.get(SpecialistProfile, specialist_id)
            if profile is None:
                return "failed"

            # Backward-compatible: old schemas might still keep calendar_id in specialist_profile.
            if hasattr(profile, "calendar_id"):
                setattr(profile, "calendar_id", normalized_calendar_id)

            settings = await session.get(SpecialistCalendarSettings, specialist_id)
            if settings is None:
                settings = SpecialistCalendarSettings(
                    specialist_id=specialist_id,
                    calendar_id=normalized_calendar_id,
                    calendar_summary=calendar_summary,
                    calendar_time_zone=calendar_tz,
                    source=SpecialistCalendarSource.selected,
                )
                session.add(settings)
            else:
                settings.calendar_id = normalized_calendar_id
                settings.calendar_summary = calendar_summary
                settings.calendar_time_zone = calendar_tz

            sync_state = await session.get(
                CalendarSyncState,
                {"specialist_id": specialist_id, "calendar_id": normalized_calendar_id},
            )
            if sync_state is None:
                sync_state = CalendarSyncState(
                    specialist_id=specialist_id,
                    calendar_id=normalized_calendar_id,
                )
                session.add(sync_state)

            sync_state.sync_token = None
            sync_state.channel_id = None
            sync_state.resource_id = None
            sync_state.channel_expiration = None
            sync_state.last_success_at = None
            sync_state.last_error_at = None
            sync_state.error_count = 0

            await session.execute(
                delete(CalendarSyncState).where(
                    CalendarSyncState.specialist_id == specialist_id,
                    CalendarSyncState.calendar_id != normalized_calendar_id,
                )
            )
            await session.commit()

        try:
            await create_and_cleanup_test_event(specialist_id, normalized_calendar_id, calendar_tz)
            smoke_status = "ok"
        except Exception as exc:
            smoke_status = "failed"
            smoke_error = str(exc)[:255]
            await _notify_specialist_integration_failed(specialist_id, smoke_error)

        async with async_session_factory() as session:
            settings = await session.get(SpecialistCalendarSettings, specialist_id)
            sync_state = await session.get(
                CalendarSyncState,
                {"specialist_id": specialist_id, "calendar_id": normalized_calendar_id},
            )
            now = datetime.now(timezone.utc)

            if settings is not None:
                settings.last_smoke_test_status = smoke_status
                settings.last_smoke_test_at = now
                settings.last_smoke_test_error = smoke_error

            if sync_state is not None:
                if smoke_status == "ok":
                    sync_state.last_success_at = now
                    sync_state.last_error_at = None
                    sync_state.error_count = 0
                else:
                    sync_state.last_error_at = now
                    sync_state.error_count = (sync_state.error_count or 0) + 1

            await session.commit()

        return smoke_status
    except Exception:
        logger.exception(
            "set_specialist_calendar failed specialist_id=%s calendar_id=%s",
            specialist_id,
            normalized_calendar_id,
        )
        return "failed"
