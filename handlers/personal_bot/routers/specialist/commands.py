from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import (
    Appointment,
    BookingState,
    Client,
    GoogleOAuthStatus,
    Specialist,
    SpecialistProfile,
    TelegramBot,
    TelegramBotStatus,
    async_session_factory,
)
from services.telegram.markdown_utils import escape_markdown_v2
from services.session_datetime import format_session_datetime

router = Router(name="personal_bot_specialist_commands")


def _specialist_status_text(state: BookingState) -> str:
    mapping = {
        BookingState.awaiting_specialist_confirmation: "Ожидает вашего подтверждения",
        BookingState.rejected_by_specialist: "Отклонено",
        BookingState.confirmed: "Подтверждена",
    }
    return mapping.get(state, str(state.value if hasattr(state, "value") else state))


def _specialist_appointments_keyboard(appointments: list[Appointment]) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for appointment in appointments:
        if appointment.booking_state != BookingState.awaiting_specialist_confirmation:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"sp_appt_decision:confirm:{appointment.appointment_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"sp_appt_decision:reject:{appointment.appointment_id}",
                ),
            ]
        )

    if not rows:
        return None

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _load_specialist_appointments(specialist_id):
    now_utc = datetime.now(timezone.utc)
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        appointments = (
            await session.execute(
                select(Appointment, Client)
                .join(Client, Client.client_id == Appointment.client_id)
                .where(Appointment.specialist_id == specialist_id)
                .where(Appointment.start_at_utc >= now_utc)
                .where(
                    Appointment.booking_state.in_(
                        (
                            BookingState.awaiting_specialist_confirmation,
                            BookingState.rejected_by_specialist,
                            BookingState.confirmed,
                        )
                    )
                )
                .order_by(Appointment.start_at_utc.asc())
                .limit(10)
            )
        ).all()

    return profile, appointments


def _status_to_text(value) -> str:
    if value is None:
        return "—"
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


async def _load_specialist_state(specialist_id):
    async with async_session_factory() as session:
        specialist_stmt = (
            select(Specialist)
            .options(
                selectinload(Specialist.google_oauth),
                selectinload(Specialist.calendar_settings),
            )
            .where(Specialist.specialist_id == specialist_id)
        )
        specialist = (await session.execute(specialist_stmt)).scalar_one_or_none()

        bot_stmt = (
            select(TelegramBot)
            .where(
                TelegramBot.specialist_id == specialist_id,
                TelegramBot.status == TelegramBotStatus.active,
            )
            .order_by(TelegramBot.updated_at.desc(), TelegramBot.created_at.desc())
        )
        active_bot = (await session.execute(bot_stmt)).scalars().first()

    return specialist, active_bot


@router.message(Command("help"))
async def personal_help(message: Message) -> None:
    await message.answer(
        "Команды специалиста:\n"
        "• /start — панель специалиста\n"
        "• /status — статус профиля и интеграций\n"
        "• /appointments — мои записи\n"
        "• /help — эта справка\n\n"
        "В разработке: управление расписанием, клиентские записи и напоминания."
    )


@router.message(Command("appointments"))
async def specialist_my_appointments(message: Message, specialist_id, actor: str) -> None:
    if actor != "specialist":
        return

    profile, appointment_rows = await _load_specialist_appointments(specialist_id)
    if not appointment_rows:
        await message.answer("У вас пока нет будущих записей.")
        return

    tz_name = profile.specialist_timezone if profile and profile.specialist_timezone else "UTC"
    try:
        specialist_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        specialist_tz = ZoneInfo("UTC")

    lines = ["Мои записи:"]
    appointments: list[Appointment] = []
    for appointment, client in appointment_rows:
        appointments.append(appointment)
        start_label = format_session_datetime(appointment.start_at_utc, specialist_tz)
        client_name = (client.display_name or client.tg_username or "Клиент").strip()
        status = _specialist_status_text(appointment.booking_state)
        lines.append(f"{start_label} — {client_name} — {status}")

    await message.answer(
        "\n".join(lines),
        reply_markup=_specialist_appointments_keyboard(appointments),
    )


@router.message(Command("status"))
@router.message(F.text == "Мой статус")
async def personal_status(message: Message, specialist_id) -> None:
    specialist, active_bot = await _load_specialist_state(specialist_id)
    if specialist is None:
        await message.answer("⚠️ Профиль специалиста не найден.")
        return

    oauth_connected = (
        specialist.google_oauth is not None
        and specialist.google_oauth.status == GoogleOAuthStatus.connected
    )

    calendar_summary = specialist.calendar_settings.calendar_summary if specialist.calendar_settings else None
    smoke_status = specialist.calendar_settings.last_smoke_test_status if specialist.calendar_settings else None

    bot_username = f"@{escape_markdown_v2(active_bot.bot_username)}" if active_bot else "—"
    onboarding_master = specialist.onboarding_master_completed_at.isoformat() if specialist.onboarding_master_completed_at else "—"
    onboarding_personal = specialist.onboarding_personal_completed_at.isoformat() if specialist.onboarding_personal_completed_at else "—"

    await message.answer(
        "📊 Состояние специалиста:\n"
        f"• Статус специалиста: {_status_to_text(specialist.status)}\n"
        f"• Personal bot: {bot_username}\n"
        f"• Google OAuth: {'connected' if oauth_connected else 'not_connected'}\n"
        f"• Календарь summary: {calendar_summary or '—'}\n"
        f"• Интеграция: {smoke_status or '—'}\n"
        f"• Onboarding (master): {onboarding_master}\n"
        f"• Onboarding (personal): {onboarding_personal}"
    )
