import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database import (
    Appointment,
    BookingState,
    Client,
    SpecialistCalendarSettings,
    SpecialistProfile,
    WeeklyAvailability,
    async_session_factory,
)
from services.availability_service import AvailabilityService
from services.booking_policy import validate_next_day_cutoff
from services.google_calendar import create_appointment_event

router = Router(name="personal_bot_client_commands")
logger = logging.getLogger(__name__)


class ClientBookingState(StatesGroup):
    waiting_for_day = State()
    waiting_for_interval = State()


_INTERVAL_META = (
    ("morning", "Утро", "interval_1_start", "interval_1_end"),
    ("day", "День", "interval_2_start", "interval_2_end"),
    ("evening", "Вечер", "interval_3_start", "interval_3_end"),
)

availability_service = AvailabilityService()


def _client_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записаться")],
            [KeyboardButton(text="Мои записи (пока stub)")],
            [KeyboardButton(text="Сменить часовой пояс (пока stub)")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("help"))
async def personal_help_client(message: Message, actor: str) -> None:
    if actor != "client":
        return
    await message.answer("Используйте /start для открытия клиентского меню.")


async def _validate_stub_booking_policy(*, specialist_id, target_start_utc: datetime) -> None:
    specialist_tz = "UTC"
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile and profile.specialist_timezone:
            specialist_tz = profile.specialist_timezone

    validate_next_day_cutoff(
        specialist_tz=specialist_tz,
        now_utc=datetime.now(timezone.utc),
        target_start_utc=target_start_utc,
        cutoff_hour_local=21,
    )


async def _get_specialist_tz(specialist_id) -> ZoneInfo:
    specialist_tz = "UTC"
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile and profile.specialist_timezone:
            specialist_tz = profile.specialist_timezone
    try:
        return ZoneInfo(specialist_tz)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _first_available_day(*, now_utc: datetime, specialist_tz: ZoneInfo) -> date:
    local_now = now_utc.astimezone(specialist_tz)
    start_offset_days = 1 if local_now.time() <= time(21, 0) else 2
    return local_now.date() + timedelta(days=start_offset_days)


def _booking_day_keyboard(days: list[date]):
    builder = InlineKeyboardBuilder()
    for booking_day in days:
        builder.button(
            text=booking_day.strftime("%d.%m (%a)"),
            callback_data=f"client_book_day:{booking_day.isoformat()}",
        )
    builder.adjust(2)
    return builder.as_markup()


def _format_interval_time_range(start: time, end: time) -> str:
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def _build_interval_options(row: WeeklyAvailability | None) -> list[tuple[str, str, time, time]]:
    if row is None or not row.is_working:
        return []

    options: list[tuple[str, str, time, time]] = []
    for key, title, start_field, end_field in _INTERVAL_META:
        start = getattr(row, start_field)
        end = getattr(row, end_field)
        if start is None or end is None:
            continue
        options.append((key, f"{title} {_format_interval_time_range(start, end)}", start, end))
    return options


def _booking_interval_keyboard(*, selected_day: date, options: list[tuple[str, str, time, time]]):
    builder = InlineKeyboardBuilder()
    for key, title, _, _ in options:
        builder.button(
            text=title,
            callback_data=f"client_book_interval:{selected_day.isoformat()}:{key}",
        )
    builder.adjust(1)
    return builder.as_markup()


async def _get_weekly_availability_row(*, specialist_id, weekday: int) -> WeeklyAvailability | None:
    async with async_session_factory() as session:
        return (
            await session.execute(
                select(WeeklyAvailability)
                .where(WeeklyAvailability.specialist_id == specialist_id)
                .where(WeeklyAvailability.weekday == weekday)
            )
        ).scalar_one_or_none()


def _booking_slots_keyboard(slots: list[datetime]):
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=slot.strftime("%H:%M"),
            callback_data=f"client_book_slot:{slot.isoformat()}",
        )
    builder.adjust(2)
    return builder.as_markup()


def _format_slot_lines(slots: list[datetime]) -> str:
    if not slots:
        return "Нет доступных слотов в выбранном диапазоне."
    return "Выберите слот:"


@router.message(F.text == "Записаться")
async def client_book_button(message: Message, actor: str, state: FSMContext, specialist_id) -> None:
    if actor != "client":
        return

    specialist_tz = await _get_specialist_tz(specialist_id)
    first_day = _first_available_day(now_utc=datetime.now(timezone.utc), specialist_tz=specialist_tz)
    available_days = [first_day + timedelta(days=idx) for idx in range(7)]

    await state.set_state(ClientBookingState.waiting_for_day)
    await state.update_data(booking_available_days=[item.isoformat() for item in available_days])
    await message.answer("Выберите день:", reply_markup=_booking_day_keyboard(available_days))


@router.callback_query(ClientBookingState.waiting_for_day, F.data.startswith("client_book_day:"))
async def client_pick_day(callback, state: FSMContext, specialist_id) -> None:
    selected_iso = callback.data.removeprefix("client_book_day:")
    selected_day = date.fromisoformat(selected_iso)
    weekly_row = await _get_weekly_availability_row(specialist_id=specialist_id, weekday=selected_day.weekday())
    interval_options = _build_interval_options(weekly_row)

    await state.set_state(ClientBookingState.waiting_for_interval)
    await state.update_data(
        booking_date=selected_iso,
        booking_interval_options=[item[0] for item in interval_options],
        booking_interval_bounds={
            item[0]: {"start": item[2].strftime("%H:%M"), "end": item[3].strftime("%H:%M")}
            for item in interval_options
        },
    )

    if not interval_options:
        await callback.message.answer("На выбранный день нет доступных диапазонов.")
        await callback.answer()
        return

    await callback.message.answer(
        "Выберите диапазон:",
        reply_markup=_booking_interval_keyboard(selected_day=selected_day, options=interval_options),
    )
    await callback.answer()


@router.callback_query(ClientBookingState.waiting_for_interval, F.data.startswith("client_book_interval:"))
async def client_pick_interval(callback, state: FSMContext, specialist_id) -> None:
    chunks = (callback.data or "").split(":", 2)
    if len(chunks) != 3:
        await callback.answer("Некорректный выбор диапазона", show_alert=True)
        return
    _, selected_iso, interval = chunks
    state_data = await state.get_data()

    if state_data.get("booking_date") != selected_iso:
        await state.update_data(booking_date=selected_iso)

    allowed_intervals = state_data.get("booking_interval_options", [])
    if interval not in allowed_intervals:
        await callback.answer("Диапазон недоступен", show_alert=True)
        return

    bounds = (state_data.get("booking_interval_bounds") or {}).get(interval)
    if not bounds:
        await callback.answer("Диапазон недоступен", show_alert=True)
        return

    interval_start = time.fromisoformat(bounds["start"])
    interval_end = time.fromisoformat(bounds["end"])
    specialist_tz = await _get_specialist_tz(specialist_id)
    slots = await availability_service.get_candidate_slots_for_date_range(
        specialist_id=specialist_id,
        target_date_local_client=date.fromisoformat(selected_iso),
        client_tz=getattr(specialist_tz, "key", "UTC"),
        interval_start=interval_start,
        interval_end=interval_end,
    )

    await callback.message.answer(
        _format_slot_lines(slots),
        reply_markup=_booking_slots_keyboard(slots) if slots else None,
    )
    await callback.answer()


@router.callback_query(ClientBookingState.waiting_for_interval, F.data.startswith("client_book_slot:"))
async def client_pick_slot(callback, state: FSMContext, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Не удалось определить пользователя", show_alert=True)
        return

    slot_raw = (callback.data or "").removeprefix("client_book_slot:")
    try:
        slot_start_local = datetime.fromisoformat(slot_raw)
    except ValueError:
        await callback.answer("Некорректный слот", show_alert=True)
        return

    specialist_tz = await _get_specialist_tz(specialist_id)
    if slot_start_local.tzinfo is None:
        slot_start_local = slot_start_local.replace(tzinfo=specialist_tz)

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if client is None:
            await callback.answer("Клиент не найден", show_alert=True)
            return

        profile = await session.get(SpecialistProfile, specialist_id)
        session_duration_min = profile.session_duration_min if profile is not None else 60

        slot_start_utc = slot_start_local.astimezone(timezone.utc)
        slot_end_utc = slot_start_utc + timedelta(minutes=session_duration_min)

        appointment = Appointment(
            specialist_id=specialist_id,
            client_id=client.client_id,
            start_at_utc=slot_start_utc,
            end_at_utc=slot_end_utc,
            booking_state=BookingState.confirmed,
            idempotency_key=f"tg:{specialist_id}:{client.client_id}:{slot_start_utc.isoformat()}",
        )
        session.add(appointment)
        await session.commit()

        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        calendar_id = settings.calendar_id if settings is not None else None
        specialist_tz_name = (
            profile.specialist_timezone
            if profile is not None and profile.specialist_timezone
            else getattr(specialist_tz, "key", "UTC")
        )

        if calendar_id:
            try:
                event = await create_appointment_event(
                    specialist_id=specialist_id,
                    calendar_id=calendar_id,
                    start_at_utc=slot_start_utc,
                    end_at_utc=slot_end_utc,
                    specialist_tz=specialist_tz_name,
                    client_display_name=client.display_name,
                    client_tg_username=client.tg_username,
                    client_tg_user_id=client.tg_user_id,
                )
            except Exception:
                logger.exception(
                    "Failed to create Google Calendar event for confirmed appointment",
                    extra={
                        "specialist_id": str(specialist_id),
                        "client_id": str(client.client_id),
                        "appointment_id": str(appointment.appointment_id),
                    },
                )
            else:
                appointment.gcal_event_id = event.get("id")
                await session.commit()

    await state.clear()
    await callback.message.answer("Запись создана", reply_markup=_client_menu_keyboard())
    await callback.answer()


@router.message(F.text == "Мои записи (пока stub)")
async def client_my_appointments_button(message: Message, actor: str) -> None:
    if actor != "client":
        return
    await message.answer("Раздел 'Мои записи' скоро будет доступен.")


@router.message(F.text == "Сменить часовой пояс (пока stub)")
async def client_change_timezone_button(message: Message, actor: str) -> None:
    if actor != "client":
        return
    await message.answer("Смена часового пояса скоро будет доступна.")


@router.message(F.text)
async def client_capture_display_name(message: Message, actor: str, specialist_id) -> None:
    if actor != "client" or message.from_user is None:
        return
    if (message.text or "").startswith("/"):
        return

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if client is None:
            return

        if client.display_name and client.display_name.strip():
            return

        client.display_name = message.text.strip()
        await session.commit()

    await message.answer(
        f"Приятно познакомиться, {message.text.strip()}!",
        reply_markup=_client_menu_keyboard(),
    )


@router.message(Command("book_stub"))
async def personal_book_stub(message: Message, command: CommandObject, specialist_id) -> None:
    """Временная заглушка будущего booking-flow с подключённой policy-проверкой."""
    if not command.args:
        await message.answer("Формат: /book_stub YYYY-MM-DDTHH:MM:SS+00:00")
        return

    try:
        target_start_utc = datetime.fromisoformat(command.args)
    except ValueError:
        await message.answer("Некорректная дата. Формат: YYYY-MM-DDTHH:MM:SS+00:00")
        return

    if target_start_utc.tzinfo is None:
        target_start_utc = target_start_utc.replace(tzinfo=timezone.utc)

    try:
        await _validate_stub_booking_policy(specialist_id=specialist_id, target_start_utc=target_start_utc)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer("✅ Заглушка: booking допустим по правилу next-day + cutoff 21:00.")


@router.message(Command("reschedule_stub"))
async def personal_reschedule_stub(message: Message, command: CommandObject, specialist_id) -> None:
    """Временная заглушка будущего reschedule-flow с подключённой policy-проверкой."""
    if not command.args:
        await message.answer("Формат: /reschedule_stub YYYY-MM-DDTHH:MM:SS+00:00")
        return

    try:
        target_start_utc = datetime.fromisoformat(command.args)
    except ValueError:
        await message.answer("Некорректная дата. Формат: YYYY-MM-DDTHH:MM:SS+00:00")
        return

    if target_start_utc.tzinfo is None:
        target_start_utc = target_start_utc.replace(tzinfo=timezone.utc)

    try:
        await _validate_stub_booking_policy(specialist_id=specialist_id, target_start_utc=target_start_utc)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer("✅ Заглушка: перенос допустим по правилу next-day + cutoff 21:00.")
