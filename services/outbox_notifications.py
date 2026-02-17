from __future__ import annotations

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.session_datetime import format_session_datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Client, NotificationLog, OutboxEvent, SpecialistProfile, TelegramBot, TelegramBotStatus
from services.telegram.bot_factory import get_personal_bot


def _parse_uuid(payload: dict, key: str) -> uuid.UUID:
    raw = payload.get(key)
    if not raw:
        raise ValueError(f"missing required payload field: {key}")
    return uuid.UUID(str(raw))


def _parse_dt(payload: dict, key: str) -> datetime:
    raw = payload.get(key)
    if not raw:
        raise ValueError(f"missing required payload field: {key}")
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)


def _format_dt_for_client(dt_utc: datetime, tz_name: str | None) -> str:
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
            return format_session_datetime(dt_utc, tz)
        except ZoneInfoNotFoundError:
            pass
    return format_session_datetime(dt_utc, ZoneInfo("UTC"))


async def _already_sent(session: AsyncSession, outbox_event_id: uuid.UUID, target: str) -> bool:
    stmt = select(NotificationLog.id).where(
        and_(
            NotificationLog.outbox_event_id == outbox_event_id,
            NotificationLog.target == target,
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _mark_sent(session: AsyncSession, outbox_event_id: uuid.UUID, target: str) -> None:
    session.add(NotificationLog(outbox_event_id=outbox_event_id, target=target))
    await session.flush()


async def _load_personal_bot(session: AsyncSession, specialist_id: uuid.UUID) -> TelegramBot | None:
    stmt = (
        select(TelegramBot)
        .where(TelegramBot.specialist_id == specialist_id)
        .where(TelegramBot.status == TelegramBotStatus.active)
        .order_by(TelegramBot.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def _send_client_message(
    session: AsyncSession,
    *,
    outbox_event: OutboxEvent,
    bot: TelegramBot,
    client: Client,
    text: str,
) -> None:
    target = f"client:{client.tg_user_id}"
    if await _already_sent(session, outbox_event.id, target):
        return
    personal_bot = await get_personal_bot(bot)
    await personal_bot.send_message(chat_id=client.tg_user_id, text=text)
    await _mark_sent(session, outbox_event.id, target)


async def _send_specialist_message(
    session: AsyncSession,
    *,
    outbox_event: OutboxEvent,
    bot: TelegramBot,
    specialist_tg_user_id: int,
    text: str,
) -> None:
    target = f"specialist:{specialist_tg_user_id}"
    if await _already_sent(session, outbox_event.id, target):
        return
    personal_bot = await get_personal_bot(bot)
    await personal_bot.send_message(chat_id=specialist_tg_user_id, text=text)
    await _mark_sent(session, outbox_event.id, target)


async def _handle_appointment_rescheduled(session: AsyncSession, event: OutboxEvent) -> None:
    payload = event.payload_json or {}
    _parse_uuid(payload, "appointment_id")
    specialist_id = _parse_uuid(payload, "specialist_id")
    client_id = _parse_uuid(payload, "client_id")
    old_start_at_utc = _parse_dt(payload, "old_start_at_utc")
    new_start_at_utc = _parse_dt(payload, "new_start_at_utc")

    client = await session.get(Client, client_id)
    specialist_profile = await session.get(SpecialistProfile, specialist_id)
    personal_bot_row = await _load_personal_bot(session, specialist_id)
    if client is None or personal_bot_row is None:
        raise ValueError("missing recipient for rescheduled notification")

    client_old = _format_dt_for_client(old_start_at_utc, client.client_timezone)
    client_new = _format_dt_for_client(new_start_at_utc, client.client_timezone)
    client_text = (
        "Специалист изменил время записи.\n"
        f"Было: {client_old}\n"
        f"Стало: {client_new}"
    )
    await _send_client_message(
        session,
        outbox_event=event,
        bot=personal_bot_row,
        client=client,
        text=client_text,
    )

    owner_tg_user_id = specialist_profile.owner_tg_user_id if specialist_profile else None
    if owner_tg_user_id is not None:
        specialist_text = (
            "Перенос записи выполнен.\n"
            f"Клиент: {client.display_name or client.client_code or client.client_id}\n"
            f"Новое время: {format_session_datetime(new_start_at_utc, ZoneInfo('UTC'))}"
        )
        await _send_specialist_message(
            session,
            outbox_event=event,
            bot=personal_bot_row,
            specialist_tg_user_id=owner_tg_user_id,
            text=specialist_text,
        )


async def _handle_appointment_cancelled_by_specialist_calendar(session: AsyncSession, event: OutboxEvent) -> None:
    payload = event.payload_json or {}
    appointment_id = _parse_uuid(payload, "appointment_id")
    specialist_id = _parse_uuid(payload, "specialist_id")
    client_id = _parse_uuid(payload, "client_id")

    client = await session.get(Client, client_id)
    specialist_profile = await session.get(SpecialistProfile, specialist_id)
    personal_bot_row = await _load_personal_bot(session, specialist_id)
    if client is None or personal_bot_row is None:
        raise ValueError("missing recipient for cancellation notification")

    client_text = f"Специалист отменил запись #{appointment_id}."
    await _send_client_message(
        session,
        outbox_event=event,
        bot=personal_bot_row,
        client=client,
        text=client_text,
    )

    owner_tg_user_id = specialist_profile.owner_tg_user_id if specialist_profile else None
    if owner_tg_user_id is not None:
        specialist_text = (
            f"Отмена записи #{appointment_id} синхронизирована.\n"
            f"Клиент: {client.display_name or client.client_code or client.client_id}"
        )
        await _send_specialist_message(
            session,
            outbox_event=event,
            bot=personal_bot_row,
            specialist_tg_user_id=owner_tg_user_id,
            text=specialist_text,
        )


from typing import Callable, Awaitable


def register_outbox_handlers(handlers: dict[str, Callable[[AsyncSession, OutboxEvent], Awaitable[None]]]) -> None:
    handlers["appointment_rescheduled"] = _handle_appointment_rescheduled
    handlers["appointment_cancelled_by_specialist_calendar"] = _handle_appointment_cancelled_by_specialist_calendar
