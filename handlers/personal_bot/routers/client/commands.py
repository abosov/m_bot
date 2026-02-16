import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

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
            [KeyboardButton(text="Мои записи")],
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


async def _get_session_duration_min(specialist_id) -> int:
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
    if profile is None or profile.session_duration_min is None:
        return 60
    return profile.session_duration_min


async def _is_day_limit_reached(*, specialist_id, day_local: date, specialist_tz: ZoneInfo) -> bool:
    day_start_local = datetime.combine(day_local, time(0, 0), tzinfo=specialist_tz)
    day_end_local = day_start_local + timedelta(days=1)
    start_utc = day_start_local.astimezone(timezone.utc)
    end_utc = day_end_local.astimezone(timezone.utc)

    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        max_sessions_per_day = 4
        if profile is not None and profile.max_sessions_per_day is not None:
            max_sessions_per_day = profile.max_sessions_per_day

        day_appointments_count = (
            await session.execute(
                select(func.count())
                .select_from(Appointment)
                .where(Appointment.specialist_id == specialist_id)
                .where(Appointment.start_at_utc >= start_utc)
                .where(Appointment.start_at_utc < end_utc)
                .where(Appointment.booking_state.in_((BookingState.confirmed, BookingState.pending)))
            )
        ).scalar_one()

    return day_appointments_count >= max_sessions_per_day


async def _get_client_tz(*, specialist_id, tg_user_id) -> ZoneInfo:
    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()

    tz_name = client.client_timezone if client and client.client_timezone else "UTC"
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _format_gmt_offset_label(tz: ZoneInfo, *, on_date: date | None = None) -> str:
    if on_date is None:
        local_dt = datetime.now(tz)
    else:
        local_dt = datetime.combine(on_date, time(12, 0), tzinfo=tz)

    offset = local_dt.utcoffset() or timedelta(0)
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    abs_seconds = abs(total_seconds)
    hours, remainder = divmod(abs_seconds, 3600)
    minutes = remainder // 60

    if minutes == 0:
        return f"GMT{sign}{hours}"
    return f"GMT{sign}{hours:02d}:{minutes:02d}"


def _first_available_day(*, now_utc: datetime, specialist_tz: ZoneInfo) -> date:
    local_now = now_utc.astimezone(specialist_tz)
    start_offset_days = 1 if local_now.time() <= time(21, 0) else 2
    return local_now.date() + timedelta(days=start_offset_days)


def _booking_day_keyboard(days: list[date], *, enabled_by_iso: dict[str, bool]):
    builder = InlineKeyboardBuilder()
    for booking_day in days:
        day_iso = booking_day.isoformat()
        is_enabled = enabled_by_iso.get(day_iso, False)
        callback_data = f"client_book_day:{day_iso}" if is_enabled else "noop"
        button_text = booking_day.strftime("%d.%m (%a)")
        if callback_data == "noop":
            button_text = f"{button_text} 🚫"
        builder.button(
            text=button_text,
            callback_data=callback_data,
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


def _booking_interval_keyboard(*, selected_day: date, options: list[tuple[str, str, time, time, bool]]):
    builder = InlineKeyboardBuilder()
    for key, title, _, _, is_enabled in options:
        callback_data = f"client_book_interval:{selected_day.isoformat()}:{key}" if is_enabled else "noop"
        button_text = f"{title} 🚫" if callback_data == "noop" else title
        builder.button(
            text=button_text,
            callback_data=callback_data,
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


async def _has_any_slots_in_day(*, specialist_id, day_local: date) -> bool:
    weekly_row = await _get_weekly_availability_row(specialist_id=specialist_id, weekday=day_local.weekday())
    if weekly_row is None or not weekly_row.is_working:
        return False

    interval_options = _build_interval_options(weekly_row)
    if not interval_options:
        return False

    specialist_tz = await _get_specialist_tz(specialist_id)
    for _, _, interval_start, interval_end in interval_options:
        slots = await availability_service.get_candidate_slots_for_date_range(
            specialist_id=specialist_id,
            target_date_local_client=day_local,
            client_tz=getattr(specialist_tz, "key", "UTC"),
            interval_start=interval_start,
            interval_end=interval_end,
        )
        if slots:
            return True

    return False


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


def _client_appointments_keyboard(*, has_failed: bool):
    builder = InlineKeyboardBuilder()
    if has_failed:
        builder.button(
            text="Повторить последнюю не подтвержденную",
            callback_data="client_appt:retry_last",
        )
    builder.button(text="Обновить", callback_data="client_appt:list")
    builder.button(text="В меню", callback_data="client_appt:menu")
    builder.adjust(1)
    return builder.as_markup()


async def _render_client_appointments(message: Message, specialist_id: UUID, tg_user_id: int) -> None:
    now_utc = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()
        if client is None:
            await message.answer("Профиль клиента не найден. Нажмите /start.")
            return

        appointments = (
            await session.execute(
                select(Appointment)
                .where(Appointment.client_id == client.client_id)
                .where(Appointment.start_at_utc >= now_utc)
                .where(Appointment.booking_state.in_((BookingState.confirmed, BookingState.failed)))
                .order_by(Appointment.start_at_utc.asc())
                .limit(10)
            )
        ).scalars().all()

    tz_name = client.client_timezone or "UTC"
    try:
        client_tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        client_tz = ZoneInfo("UTC")

    if not appointments:
        text = "У вас нет будущих записей."
        has_failed = False
    else:
        state_map = {
            BookingState.confirmed: "подтверждена",
            BookingState.failed: "не подтверждена",
        }
        has_failed = any(appointment.booking_state == BookingState.failed for appointment in appointments)
        lines = ["Ваши записи:"]
        for appointment in appointments:
            local_start = appointment.start_at_utc.astimezone(client_tz)
            status = state_map.get(appointment.booking_state, str(appointment.booking_state))
            lines.append(f"{local_start.strftime('%Y-%m-%d %H:%M')} — {status}")
        text = "\n".join(lines)

    await message.answer(text, reply_markup=_client_appointments_keyboard(has_failed=has_failed))


@router.message(F.text == "Записаться")
async def client_book_button(message: Message, actor: str, state: FSMContext, specialist_id) -> None:
    if actor != "client":
        return

    specialist_tz = await _get_specialist_tz(specialist_id)
    first_day = _first_available_day(now_utc=datetime.now(timezone.utc), specialist_tz=specialist_tz)
    available_days = [first_day + timedelta(days=idx) for idx in range(7)]
    enabled_by_iso: dict[str, bool] = {}
    booking_day_meta: dict[str, dict[str, bool]] = {}
    for booking_day in available_days:
        weekly_row = await _get_weekly_availability_row(specialist_id=specialist_id, weekday=booking_day.weekday())
        is_working_day = weekly_row is not None and weekly_row.is_working
        is_day_limit_reached = (
            await _is_day_limit_reached(specialist_id=specialist_id, day_local=booking_day, specialist_tz=specialist_tz)
            if is_working_day
            else False
        )
        has_slots_in_day = (
            await _has_any_slots_in_day(specialist_id=specialist_id, day_local=booking_day)
            if is_working_day and not is_day_limit_reached
            else False
        )
        is_enabled = is_working_day and not is_day_limit_reached and has_slots_in_day
        day_iso = booking_day.isoformat()
        enabled_by_iso[day_iso] = is_enabled
        booking_day_meta[day_iso] = {
            "is_working": is_working_day,
            "limit_reached": is_day_limit_reached,
            "has_any_slots": has_slots_in_day,
            "enabled": is_enabled,
        }
    client_tz = (
        await _get_client_tz(specialist_id=specialist_id, tg_user_id=message.from_user.id)
        if message.from_user is not None
        else ZoneInfo("UTC")
    )
    gmt_label = _format_gmt_offset_label(client_tz)

    await state.set_state(ClientBookingState.waiting_for_day)
    await state.update_data(
        booking_available_days=[item.isoformat() for item in available_days],
        booking_day_meta=booking_day_meta,
        booking_interval_meta={},
    )
    await message.answer(
        f"Выберите день ({gmt_label}):",
        reply_markup=_booking_day_keyboard(available_days, enabled_by_iso=enabled_by_iso),
    )


@router.callback_query(ClientBookingState.waiting_for_day, F.data.startswith("client_book_day:"))
async def client_pick_day(callback, state: FSMContext, specialist_id) -> None:
    selected_iso = callback.data.removeprefix("client_book_day:")
    selected_day = date.fromisoformat(selected_iso)
    state_data = await state.get_data()
    booking_day_meta = state_data.get("booking_day_meta") or {}
    if not (booking_day_meta.get(selected_iso) or {}).get("enabled", False):
        await callback.answer("День недоступен", show_alert=True)
        return

    client_tz = (
        await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
        if callback.from_user is not None
        else ZoneInfo("UTC")
    )
    gmt_label = _format_gmt_offset_label(client_tz, on_date=selected_day)
    weekly_row = await _get_weekly_availability_row(specialist_id=specialist_id, weekday=selected_day.weekday())
    interval_options = _build_interval_options(weekly_row)
    specialist_tz = await _get_specialist_tz(specialist_id)
    session_duration_min = await _get_session_duration_min(specialist_id)
    booking_interval_meta = state_data.get("booking_interval_meta") or {}

    if selected_iso not in booking_interval_meta:
        booking_interval_meta[selected_iso] = {}
        for key, _, interval_start, interval_end in interval_options:
            slots = await availability_service.get_candidate_slots_for_date_range(
                specialist_id=specialist_id,
                target_date_local_client=selected_day,
                client_tz=getattr(specialist_tz, "key", "UTC"),
                interval_start=interval_start,
                interval_end=interval_end,
            )
            booking_interval_meta[selected_iso][key] = {
                "enabled": bool(slots),
                "slot_count": len(slots),
            }

    day_interval_meta = booking_interval_meta.get(selected_iso) or {}
    interval_enabled = {key: bool((day_interval_meta.get(key) or {}).get("enabled", False)) for key, _, _, _ in interval_options}
    interval_options_with_enabled: list[tuple[str, str, time, time, bool]] = []
    for key, title, interval_start, interval_end in interval_options:
        is_enabled = interval_enabled.get(key, False)
        interval_options_with_enabled.append((key, title, interval_start, interval_end, is_enabled))

    await state.set_state(ClientBookingState.waiting_for_interval)
    await state.update_data(
        booking_date=selected_iso,
        booking_interval_options=[item[0] for item in interval_options],
        booking_interval_enabled=interval_enabled,
        booking_interval_meta=booking_interval_meta,
        booking_session_duration_min=session_duration_min,
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
        f"Выберите диапазон ({gmt_label}):",
        reply_markup=_booking_interval_keyboard(selected_day=selected_day, options=interval_options_with_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback) -> None:
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

    interval_meta = ((state_data.get("booking_interval_meta") or {}).get(selected_iso) or {}).get(interval)
    interval_enabled = interval_meta.get("enabled") if isinstance(interval_meta, dict) else None
    if interval_enabled is None:
        interval_enabled = (state_data.get("booking_interval_enabled") or {}).get(interval)
    if interval_enabled is False:
        await callback.answer("Диапазон недоступен", show_alert=True)
        return

    bounds = (state_data.get("booking_interval_bounds") or {}).get(interval)
    if not bounds:
        await callback.answer("Диапазон недоступен", show_alert=True)
        return

    interval_start = time.fromisoformat(bounds["start"])
    interval_end = time.fromisoformat(bounds["end"])
    selected_day = date.fromisoformat(selected_iso)
    client_tz = (
        await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
        if callback.from_user is not None
        else ZoneInfo("UTC")
    )
    gmt_label = _format_gmt_offset_label(client_tz, on_date=selected_day)
    specialist_tz = await _get_specialist_tz(specialist_id)
    slots = await availability_service.get_candidate_slots_for_date_range(
        specialist_id=specialist_id,
        target_date_local_client=selected_day,
        client_tz=getattr(specialist_tz, "key", "UTC"),
        interval_start=interval_start,
        interval_end=interval_end,
    )

    header = (
        f"Выберите слот ({gmt_label}):"
        if slots
        else f"Нет доступных слотов в выбранном диапазоне ({gmt_label})."
    )

    await callback.message.answer(
        header,
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
        session_duration_min = await _get_session_duration_min(specialist_id)

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
                    client_code=client.client_code,
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


@router.message(F.text.in_({"Мои записи", "Мои записи (пока stub)"}))
async def client_my_appointments_button(message: Message, actor: str, specialist_id) -> None:
    if actor != "client":
        return
    if message.from_user is None:
        return
    await _render_client_appointments(message, specialist_id, message.from_user.id)


@router.callback_query(F.data == "client_appt:list")
async def client_my_appointments_refresh(callback, specialist_id) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)


@router.callback_query(F.data == "client_appt:retry_last")
async def client_my_appointments_retry_last(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
        return

    now_utc = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if client is None:
            await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
            return

        appointment = (
            await session.execute(
                select(Appointment)
                .where(Appointment.client_id == client.client_id)
                .where(Appointment.booking_state == BookingState.failed)
                .where(Appointment.start_at_utc >= now_utc)
                .order_by(Appointment.start_at_utc.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if appointment is None:
            await callback.answer("Нет записей для повтора", show_alert=True)
            return

        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        calendar_id = settings.calendar_id if settings is not None else None
        if not calendar_id:
            if callback.message is not None:
                await callback.message.answer("Запись временно недоступна: календарь не подключён.")
                await callback.message.answer("Возвращаю в меню.", reply_markup=_client_menu_keyboard())
            await callback.answer()
            return

        profile = await session.get(SpecialistProfile, specialist_id)
        specialist_tz = (
            profile.specialist_timezone if profile is not None and profile.specialist_timezone else "UTC"
        )

        appointment.booking_state = BookingState.pending
        appointment.failure_message = None
        await session.commit()

        try:
            event = await create_appointment_event(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                start_at_utc=appointment.start_at_utc,
                end_at_utc=appointment.end_at_utc,
                specialist_tz=specialist_tz,
                client_display_name=client.display_name,
                client_tg_username=client.tg_username,
                client_tg_user_id=client.tg_user_id,
                client_code=client.client_code,
            )
        except Exception:
            appointment.booking_state = BookingState.failed
            appointment.failure_message = "google_error"
            await session.commit()
            if callback.message is not None:
                await callback.message.answer("Не удалось подтвердить запись. Попробуйте позже.")
        else:
            appointment.gcal_event_id = event.get("id")
            appointment.booking_state = BookingState.confirmed
            await session.commit()
            if callback.message is not None:
                await callback.message.answer("Запись подтверждена.")

    if callback.message is not None:
        await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "client_appt:menu")
async def client_my_appointments_to_menu(callback) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.answer("Возвращаю в меню.", reply_markup=_client_menu_keyboard())


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
