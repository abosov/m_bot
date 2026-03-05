import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.personal_bot.ui.timezones import MAX_TZ_PAGE, build_timezone_keyboard
from handlers.personal_bot.routers.common import start as start_router
from sqlalchemy import func, select

from database import (
    Appointment,
    AppointmentCalendarLink,
    BookingState,
    Client,
    ClientTimezoneSource,
    OutboxEvent,
    SpecialistCalendarSettings,
    SpecialistProfile,
    TariffPlan,
    WeeklyAvailability,
    async_session_factory,
)
from services.availability_service import AvailabilityService
from services.booking_policy import validate_min_hours_before_start
from services.google_calendar import create_appointment_event
from services.google_calendar import delete_appointment_event
from services.google_calendar import update_appointment_event
from services.google_oauth import assert_calendar_ready_for_booking
from services.appointment_state_guard import (
    InvalidAppointmentTransitionError,
    mark_google_create_failed,
    mark_google_create_succeeded,
)
from services.outbox import emit_domain_event as emit_outbox_domain_event
from services.session_datetime import format_session_datetime
from services.request_context import get_request_id
from services.plan_limits import PlanLimitError, enforce_booking_plan_limit
from services.upsell import (
    maybe_mark_analytics_upsell_needed,
    upsell_button_text,
    upsell_message_text,
    upsell_pricing_url,
)

router = Router(name="personal_bot_client_commands")
logger = logging.getLogger(__name__)


class ClientBookingState(StatesGroup):
    waiting_for_day = State()
    waiting_for_interval = State()


class ClientTimezoneState(StatesGroup):
    waiting_for_timezone = State()


class ClientReminderCancelCommentState(StatesGroup):
    waiting_for_text = State()



_INTERVAL_META = (
    ("morning", "Утро", "interval_1_start", "interval_1_end"),
    ("day", "День", "interval_2_start", "interval_2_end"),
    ("evening", "Вечер", "interval_3_start", "interval_3_end"),
)

RU_WEEKDAY_SHORT = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

availability_service = AvailabilityService()


def _normalize_tz_input(raw: str) -> str:
    return " ".join(raw.strip().replace("\\", "/").split())


def _validate_tz_name(tz_name: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return None


def _parse_google_event_updated(raw_updated: str | None):
    if not raw_updated:
        return None
    try:
        return datetime.fromisoformat(raw_updated.replace("Z", "+00:00"))
    except ValueError:
        return None


async def _upsert_appointment_calendar_link(
    *,
    session,
    appointment_id,
    specialist_id,
    calendar_id: str,
    google_event_id: str,
    google_event: dict,
) -> None:
    link = await session.get(AppointmentCalendarLink, appointment_id)
    if link is None:
        link = AppointmentCalendarLink(
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            calendar_id=calendar_id,
            google_event_id=google_event_id,
        )
        session.add(link)

    link.specialist_id = specialist_id
    link.calendar_id = calendar_id
    link.google_event_id = google_event_id
    link.ical_uid = google_event.get("iCalUID")
    link.event_etag = google_event.get("etag")
    link.event_updated = _parse_google_event_updated(google_event.get("updated"))
    link.last_synced_at = datetime.now(timezone.utc)


def _client_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Записаться")],
            [KeyboardButton(text="Мои записи")],
            [KeyboardButton(text="Сменить часовой пояс")],
            [KeyboardButton(text="🏠 В меню")],
        ],
        resize_keyboard=True,
    )


def _client_fallback_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 В меню")],
            [KeyboardButton(text="/start")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("help"))
async def personal_help_client(message: Message, actor: str) -> None:
    if actor != "client":
        return
    await message.answer("Используйте /start для открытия клиентского меню.")


async def _resolve_cancel_window_hours(*, specialist_id) -> int:
    async with async_session_factory() as session:
        if not hasattr(session, "get"):
            return 12
        profile = await session.get(SpecialistProfile, specialist_id)
    cancel_window_hours = getattr(profile, "cancel_window_hours", None)
    if cancel_window_hours is None:
        return 12
    return cancel_window_hours


async def _validate_min_hours_policy(*, specialist_id, target_start_utc: datetime) -> None:
    min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
    validate_min_hours_before_start(
        now_utc=datetime.now(timezone.utc),
        target_start_utc=target_start_utc,
        min_hours=min_hours,
    )


async def _load_client_and_appointment_for_callback(*, session, specialist_id, tg_user_id: int, appointment_id: UUID):
    client = (
        await session.execute(
            select(Client)
            .where(Client.specialist_id == specialist_id)
            .where(Client.tg_user_id == tg_user_id)
        )
    ).scalar_one_or_none()
    if client is None:
        return None, None

    appointment = (
        await session.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .where(Appointment.client_id == client.client_id)
            .where(Appointment.specialist_id == specialist_id)
        )
    ).scalar_one_or_none()
    return client, appointment


async def _cancel_client_appointment(
    *,
    session,
    specialist_id,
    client,
    appointment,
    comment: str | None = None,
) -> None:
    try:
        if appointment.booking_state != BookingState.confirmed:
            raise InvalidAppointmentTransitionError("client cancellation requires confirmed state")
        appointment.booking_state = BookingState.canceled_by_client
    except InvalidAppointmentTransitionError:
        raise ValueError("Отмена доступна только для подтверждённой записи.") from None

    settings = await session.get(SpecialistCalendarSettings, specialist_id)
    calendar_id = settings.calendar_id if settings is not None else None
    if calendar_id and appointment.gcal_event_id:
        await delete_appointment_event(
            specialist_id=specialist_id,
            calendar_id=calendar_id,
            google_event_id=appointment.gcal_event_id,
        )

    payload = {
        "appointment_id": str(appointment.appointment_id),
        "specialist_id": str(specialist_id),
        "client_id": str(client.client_id),
        "start_at_utc": appointment.start_at_utc.isoformat(),
    }
    if comment:
        payload["comment"] = comment
    await emit_outbox_domain_event(session, "appointment_cancelled_by_client", payload)


def _contact_idempotency_key(*, appointment_id: UUID, now_utc: datetime) -> tuple[str, datetime, datetime]:
    floored_minute = (now_utc.minute // 5) * 5
    bucket_start = now_utc.replace(minute=floored_minute, second=0, microsecond=0)
    bucket_end = bucket_start + timedelta(minutes=5)
    bucket_code = bucket_start.strftime("%Y%m%d%H%M")
    return f"contact:{appointment_id}:{bucket_code}", bucket_start, bucket_end


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
                .where(
                    Appointment.booking_state.in_(
                        (
                            BookingState.confirmed,
                            BookingState.pending,
                            BookingState.awaiting_specialist_confirmation,
                        )
                    )
                )
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


async def _ensure_client_exists(*, session, specialist_id, tg_user) -> Client:
    client = (
        await session.execute(
            select(Client)
            .where(Client.specialist_id == specialist_id)
            .where(Client.tg_user_id == tg_user.id)
        )
    ).scalar_one_or_none()
    if client is not None:
        return client

    profile = await session.get(SpecialistProfile, specialist_id)
    specialist_timezone = profile.specialist_timezone if profile and profile.specialist_timezone else "UTC"

    display_name = getattr(tg_user, "full_name", None)
    if not display_name:
        first_name = getattr(tg_user, "first_name", None)
        last_name = getattr(tg_user, "last_name", None)
        display_name = " ".join(part for part in [first_name, last_name] if part).strip() or "Клиент"

    client = Client(
        specialist_id=specialist_id,
        tg_user_id=tg_user.id,
        tg_username=getattr(tg_user, "username", None),
        display_name=display_name,
        client_code=f"tg-{tg_user.id}",
        client_timezone=specialist_timezone,
        timezone_source=ClientTimezoneSource.default_from_specialist,
    )
    session.add(client)
    await session.commit()
    return client


async def _has_registered_client_name(*, specialist_id, tg_user_id: int) -> bool:
    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()
    if client is None:
        return False
    display_name = getattr(client, "display_name", None)
    if display_name is None:
        return True
    return bool(str(display_name).strip())


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
        return f"UTC{sign}{hours}"
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _format_session_datetime_without_brackets(dt: datetime, tz: ZoneInfo) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_dt = dt.astimezone(tz)
    weekday_short = RU_WEEKDAY_SHORT[local_dt.weekday()]
    return f"{local_dt:%Y-%m-%d} {weekday_short} {local_dt:%H:%M}"


def _first_available_day(*, now_utc: datetime, specialist_tz: ZoneInfo, min_hours: int) -> date:
    first_allowed = now_utc + timedelta(hours=min_hours)
    return first_allowed.astimezone(specialist_tz).date()


def _booking_day_keyboard(days: list[date], *, enabled_by_iso: dict[str, bool]):
    builder = InlineKeyboardBuilder()
    for booking_day in days:
        day_iso = booking_day.isoformat()
        is_enabled = enabled_by_iso.get(day_iso, False)
        callback_data = f"client_book_day:{day_iso}" if is_enabled else "noop"
        weekday_ru = RU_WEEKDAY_SHORT[booking_day.weekday()]
        button_text = f"{booking_day:%d.%m} ({weekday_ru})"
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


def _format_interval_title_for_client_tz(
    *, base_title: str, start_local: time, end_local: time, on_date: date, specialist_tz: ZoneInfo, client_tz: ZoneInfo
) -> str:
    start_dt_sp = datetime.combine(on_date, start_local, tzinfo=specialist_tz)
    end_dt_sp = datetime.combine(on_date, end_local, tzinfo=specialist_tz)

    start_dt_cl = start_dt_sp.astimezone(client_tz)
    end_dt_cl = end_dt_sp.astimezone(client_tz)

    return f"{base_title} ({start_dt_cl:%H:%M}–{end_dt_cl:%H:%M})"


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


async def _has_any_slots_in_day(*, specialist_id, day_local: date, client_tz: ZoneInfo) -> bool:
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
            client_tz=getattr(client_tz, "key", "UTC"),
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


def _client_appointments_keyboard(*, has_failed: bool, confirmed_appointments: list[tuple[UUID, str]]):
    builder = InlineKeyboardBuilder()
    for appointment_id, formatted_start in confirmed_appointments:
        builder.button(
            text=f"Открыть {formatted_start}",
            callback_data=f"client_appt:view:{appointment_id}",
        )
    if has_failed:
        builder.button(
            text="Повторить последнюю не подтвержденную",
            callback_data="client_appt:retry_last",
        )
    builder.button(text="Обновить", callback_data="client_appt:list")
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
                .where(
                    Appointment.booking_state.in_(
                        (
                            BookingState.confirmed,
                            BookingState.failed,
                            BookingState.awaiting_specialist_confirmation,
                            BookingState.rejected_by_specialist,
                        )
                    )
                )
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
            BookingState.confirmed: "Подтверждена",
            BookingState.failed: "Не подтверждена",
            BookingState.awaiting_specialist_confirmation: "Ожидает подтверждения",
            BookingState.rejected_by_specialist: "❌ Отклонено",
        }
        has_failed = any(appointment.booking_state == BookingState.failed for appointment in appointments)
        confirmed_appointments: list[tuple[UUID, str]] = []
        gmt_label = _format_gmt_offset_label(client_tz)
        lines = [f"Ваши записи ({gmt_label}):"]
        for appointment in appointments:
            formatted_start = format_session_datetime(appointment.start_at_utc, client_tz)
            status = state_map.get(appointment.booking_state, str(appointment.booking_state))
            lines.append(f"{formatted_start} — {status}")
            if appointment.booking_state == BookingState.rejected_by_specialist and appointment.rejection_reason:
                lines.append(f"Комментарий: {appointment.rejection_reason}")
            if appointment.booking_state == BookingState.confirmed:
                confirmed_appointments.append((appointment.appointment_id, formatted_start))
        text = "\n".join(lines)
    if not appointments:
        confirmed_appointments = []

    await message.answer(
        text,
        reply_markup=_client_appointments_keyboard(has_failed=has_failed, confirmed_appointments=confirmed_appointments),
    )


@router.message(F.text == "Записаться")
async def client_book_button(message: Message, actor: str, state: FSMContext, specialist_id) -> None:
    if actor != "client":
        return

    await assert_calendar_ready_for_booking(specialist_id)

    if message.from_user is not None:
        is_registered = await _has_registered_client_name(specialist_id=specialist_id, tg_user_id=message.from_user.id)
        if not is_registered:
            await state.clear()
            await start_router.recover_client_entrypoint(
                message,
                specialist_id=specialist_id,
                where="client_book_button:recover_unregistered",
                bot_user_id=getattr(getattr(message, "bot", None), "id", None),
            )
            return

    specialist_tz = await _get_specialist_tz(specialist_id)
    min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
    first_day = _first_available_day(now_utc=datetime.now(timezone.utc), specialist_tz=specialist_tz, min_hours=min_hours)
    available_days = [first_day + timedelta(days=idx) for idx in range(7)]
    client_tz = (
        await _get_client_tz(specialist_id=specialist_id, tg_user_id=message.from_user.id)
        if message.from_user is not None
        else ZoneInfo("UTC")
    )
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
            await _has_any_slots_in_day(specialist_id=specialist_id, day_local=booking_day, client_tz=client_tz)
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
    gmt_label = _format_gmt_offset_label(client_tz)

    await state.set_state(ClientBookingState.waiting_for_day)
    await state.update_data(
        booking_available_days=[item.isoformat() for item in available_days],
        booking_day_meta=booking_day_meta,
        booking_interval_meta={},
    )
    await message.answer(
        "Выберите день для сессии:",
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

    if callback.from_user is not None:
        async with async_session_factory() as session:
            await _ensure_client_exists(session=session, specialist_id=specialist_id, tg_user=callback.from_user)

    client_tz = (
        await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
        if callback.from_user is not None
        else ZoneInfo("UTC")
    )
    gmt_label = _format_gmt_offset_label(client_tz, on_date=selected_day)
    weekly_row = await _get_weekly_availability_row(specialist_id=specialist_id, weekday=selected_day.weekday())
    interval_options = _build_interval_options(weekly_row)
    specialist_tz = await _get_specialist_tz(specialist_id)
    interval_options_for_ui: list[tuple[str, str, time, time]] = []
    for key, title, interval_start, interval_end in interval_options:
        base_title = title.split(" ", 1)[0]
        interval_options_for_ui.append(
            (
                key,
                _format_interval_title_for_client_tz(
                    base_title=base_title,
                    start_local=interval_start,
                    end_local=interval_end,
                    on_date=selected_day,
                    specialist_tz=specialist_tz,
                    client_tz=client_tz,
                ),
                interval_start,
                interval_end,
            )
        )
    session_duration_min = await _get_session_duration_min(specialist_id)
    booking_interval_meta = state_data.get("booking_interval_meta") or {}

    if selected_iso not in booking_interval_meta:
        booking_interval_meta[selected_iso] = {}
        for key, _, interval_start, interval_end in interval_options:
            slots = await availability_service.get_candidate_slots_for_date_range(
                specialist_id=specialist_id,
                target_date_local_client=selected_day,
                client_tz=getattr(client_tz, "key", "UTC"),
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
    for key, title, interval_start, interval_end in interval_options_for_ui:
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
    if callback.from_user is not None:
        async with async_session_factory() as session:
            await _ensure_client_exists(session=session, specialist_id=specialist_id, tg_user=callback.from_user)

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
        client_tz=getattr(client_tz, "key", "UTC"),
        interval_start=interval_start,
        interval_end=interval_end,
    )
    client_slots: list[datetime] = []
    for slot in slots:
        slot_sp = slot.replace(tzinfo=specialist_tz) if slot.tzinfo is None else slot.astimezone(specialist_tz)
        client_slots.append(slot_sp.astimezone(client_tz))

    header = (
        f"Выберите слот ({gmt_label}):"
        if client_slots
        else f"Нет доступных слотов в выбранном диапазоне ({gmt_label})."
    )

    await callback.message.answer(
        header,
        reply_markup=_booking_slots_keyboard(client_slots) if client_slots else None,
    )
    await callback.answer()


@router.callback_query(ClientBookingState.waiting_for_interval, F.data.startswith("client_book_slot:"))
async def client_pick_slot(callback, state: FSMContext, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Не удалось определить пользователя", show_alert=True)
        return

    await assert_calendar_ready_for_booking(specialist_id)

    slot_raw = (callback.data or "").removeprefix("client_book_slot:")
    try:
        slot_start_local = datetime.fromisoformat(slot_raw)
    except ValueError:
        await callback.answer("Некорректный слот", show_alert=True)
        return

    specialist_tz = await _get_specialist_tz(specialist_id)
    client_tz = await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
    if slot_start_local.tzinfo is None:
        slot_start_local = slot_start_local.replace(tzinfo=client_tz)

    async with async_session_factory() as session:
        client = await _ensure_client_exists(session=session, specialist_id=specialist_id, tg_user=callback.from_user)

        profile = await session.get(SpecialistProfile, specialist_id)
        session_duration_min = await _get_session_duration_min(specialist_id)

        slot_start_utc = slot_start_local.astimezone(timezone.utc)
        slot_end_utc = slot_start_utc + timedelta(minutes=session_duration_min)

        existing_rejected_appointment = (
            await session.execute(
                select(Appointment)
                .where(Appointment.specialist_id == specialist_id)
                .where(Appointment.start_at_utc == slot_start_utc)
                .where(Appointment.booking_state == BookingState.rejected_by_specialist)
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing_rejected_appointment is not None and getattr(existing_rejected_appointment, "booking_state", None) == BookingState.rejected_by_specialist:
            await state.clear()
            blocked_slot_text = _format_session_datetime_without_brackets(slot_start_utc, client_tz)
            await callback.message.answer(
                "Вы уже запрашивали запись на это время.\n\n"
                f"Дата и время: {blocked_slot_text}\n\n"
                "Специалист ранее отклонил этот запрос.\n"
                "Пожалуйста, выберите другое время.",
            )
            await start_router.render_client_menu(
                callback.message,
                where="client_pick_slot:rejected_slot",
                specialist_id=specialist_id,
                bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
            )
            await callback.answer()
            return

        try:
            await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=slot_start_utc)
            await enforce_booking_plan_limit(
                session=session,
                profile=profile,
                specialist_id=specialist_id,
                slot_start_utc=slot_start_utc,
            )
        except (ValueError, PlanLimitError) as exc:
            await callback.answer(str(exc), show_alert=True)
            return

        tariff_plan = getattr(profile, "tariff_plan", TariffPlan.start)

        appointment = Appointment(
            specialist_id=specialist_id,
            client_id=client.client_id,
            start_at_utc=slot_start_utc,
            end_at_utc=slot_end_utc,
            booking_state=BookingState.pending,
            idempotency_key=f"tg:{specialist_id}:{client.client_id}:{slot_start_utc.isoformat()}",
        )
        session.add(appointment)
        await session.commit()

        should_send_upsell = await maybe_mark_analytics_upsell_needed(
            session=session,
            profile=profile,
            specialist_id=specialist_id,
        )
        if should_send_upsell:
            await session.commit()
            owner_tg_user_id = getattr(profile, "owner_tg_user_id", None)
            bot_instance = getattr(callback, "bot", None)
            if owner_tg_user_id is not None and bot_instance is not None:
                try:
                    await bot_instance.send_message(
                        chat_id=owner_tg_user_id,
                        text=upsell_message_text(),
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text=upsell_button_text(), url=upsell_pricing_url())]]
                        ),
                    )
                except Exception:
                    logger.warning(
                        "Failed to send analytics upsell message specialist_id=%s owner_tg_user_id=%s",
                        specialist_id,
                        owner_tg_user_id,
                        exc_info=True,
                    )

        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        calendar_id = settings.calendar_id if settings is not None else None
        specialist_tz_name = (
            profile.specialist_timezone
            if profile is not None and profile.specialist_timezone
            else getattr(specialist_tz, "key", "UTC")
        )

        if calendar_id:
            try:
                if appointment.gcal_event_id:
                    event = await update_appointment_event(
                        appointment_id=appointment.appointment_id,
                        specialist_id=specialist_id,
                        calendar_id=calendar_id,
                        google_event_id=appointment.gcal_event_id,
                        start_at_utc=slot_start_utc,
                        end_at_utc=slot_end_utc,
                        specialist_tz=specialist_tz_name,
                        client_display_name=client.display_name,
                        client_tg_username=client.tg_username,
                        client_code=client.client_code,
                    )
                else:
                    event = await create_appointment_event(
                        appointment_id=appointment.appointment_id,
                        specialist_id=specialist_id,
                        calendar_id=calendar_id,
                        start_at_utc=slot_start_utc,
                        end_at_utc=slot_end_utc,
                        specialist_tz=specialist_tz_name,
                        client_display_name=client.display_name,
                        client_tg_username=client.tg_username,
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
                mark_google_create_failed(appointment, specialist_id=specialist_id)
                await session.commit()
            else:
                mark_google_create_succeeded(
                    appointment,
                    specialist_id=specialist_id,
                    google_event_id=event.get("id"),
                )
                await emit_outbox_domain_event(
                    session,
                    event_type="appointment_needs_confirmation",
                    payload={
                        "appointment_id": str(appointment.appointment_id),
                        "specialist_id": str(appointment.specialist_id),
                        "client_id": str(appointment.client_id),
                        "start_at_utc": appointment.start_at_utc.isoformat(),
                        "end_at_utc": appointment.end_at_utc.isoformat(),
                        "tariff_plan": tariff_plan.value if isinstance(tariff_plan, TariffPlan) else str(tariff_plan),
                    },
                )
                try:
                    await _upsert_appointment_calendar_link(
                        session=session,
                        appointment_id=appointment.appointment_id,
                        specialist_id=specialist_id,
                        calendar_id=calendar_id,
                        google_event_id=appointment.gcal_event_id,
                        google_event=event,
                    )
                except Exception:
                    logger.exception(
                        "Failed to upsert appointment_calendar_link after Google Calendar sync",
                        extra={
                            "specialist_id": str(specialist_id),
                            "appointment_id": str(appointment.appointment_id),
                            "calendar_id": calendar_id,
                            "google_event_id": appointment.gcal_event_id,
                        },
                    )
                await session.commit()

    confirmation_text = (
        "Заявка отправлена специалисту, ожидает подтверждения\n\n"
        f"{format_session_datetime(slot_start_utc, client_tz)}"
    )

    await state.clear()
    await callback.message.answer(confirmation_text)
    await start_router.render_client_menu(
        callback.message,
        where="client_pick_slot:confirmation",
        specialist_id=specialist_id,
        bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
    )
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
                await callback.message.answer("Возвращаю в меню.")
                await start_router.render_client_menu(
                    callback.message,
                    where="client_retry_last_appointment:menu",
                    specialist_id=specialist_id,
                    bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
                )
            await callback.answer()
            return

        profile = await session.get(SpecialistProfile, specialist_id)
        specialist_tz = (
            profile.specialist_timezone if profile is not None and profile.specialist_timezone else "UTC"
        )

        try:
            await _validate_min_hours_policy(
                specialist_id=specialist_id,
                target_start_utc=appointment.start_at_utc,
            )
        except ValueError as exc:
            if callback.message is not None:
                await callback.message.answer(str(exc))
            await callback.answer()
            return

        appointment.booking_state = BookingState.pending
        appointment.failure_message = None
        await session.commit()

        try:
            if appointment.gcal_event_id:
                event = await update_appointment_event(
                    appointment_id=appointment.appointment_id,
                    specialist_id=specialist_id,
                    calendar_id=calendar_id,
                    google_event_id=appointment.gcal_event_id,
                    start_at_utc=appointment.start_at_utc,
                    end_at_utc=appointment.end_at_utc,
                    specialist_tz=specialist_tz,
                    client_display_name=client.display_name,
                    client_tg_username=client.tg_username,
                    client_code=client.client_code,
                )
            else:
                event = await create_appointment_event(
                    appointment_id=appointment.appointment_id,
                    specialist_id=specialist_id,
                    calendar_id=calendar_id,
                    start_at_utc=appointment.start_at_utc,
                    end_at_utc=appointment.end_at_utc,
                    specialist_tz=specialist_tz,
                    client_display_name=client.display_name,
                    client_tg_username=client.tg_username,
                    client_code=client.client_code,
                )
        except Exception:
            mark_google_create_failed(appointment, specialist_id=specialist_id)
            await session.commit()
            if callback.message is not None:
                await callback.message.answer("Не удалось подтвердить запись. Попробуйте позже.")
        else:
            mark_google_create_succeeded(
                appointment,
                specialist_id=specialist_id,
                google_event_id=event.get("id"),
            )
            await emit_outbox_domain_event(
                session,
                event_type="appointment_needs_confirmation",
                payload={
                    "appointment_id": str(appointment.appointment_id),
                    "specialist_id": str(appointment.specialist_id),
                    "client_id": str(appointment.client_id),
                    "start_at_utc": appointment.start_at_utc.isoformat(),
                    "end_at_utc": appointment.end_at_utc.isoformat(),
                },
            )
            try:
                await _upsert_appointment_calendar_link(
                    session=session,
                    appointment_id=appointment.appointment_id,
                    specialist_id=specialist_id,
                    calendar_id=calendar_id,
                    google_event_id=appointment.gcal_event_id,
                    google_event=event,
                )
            except Exception:
                logger.exception(
                    "Failed to upsert appointment_calendar_link after Google Calendar sync",
                    extra={
                        "specialist_id": str(specialist_id),
                        "appointment_id": str(appointment.appointment_id),
                        "calendar_id": calendar_id,
                        "google_event_id": appointment.gcal_event_id,
                    },
                )
            await session.commit()
            if callback.message is not None:
                await callback.message.answer("Заявка отправлена специалисту, ожидает подтверждения.")

    if callback.message is not None:
        await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("client_appt:view:"))
async def client_appointment_view(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
        return
    if callback.message is None:
        await callback.answer()
        return

    appointment_id_raw = callback.data.removeprefix("client_appt:view:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись не найдена", show_alert=True)
        return

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
                .where(Appointment.appointment_id == appointment_id)
                .where(Appointment.client_id == client.client_id)
                .where(Appointment.specialist_id == specialist_id)
            )
        ).scalar_one_or_none()

    if appointment is None:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    client_tz = await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
    specialist_tz = await _get_specialist_tz(specialist_id)

    details_lines = [f"Запись: {format_session_datetime(appointment.start_at_utc, client_tz)}"]
    if getattr(client_tz, "key", "UTC") != getattr(specialist_tz, "key", "UTC"):
        details_lines.append(f"По времени специалиста: {format_session_datetime(appointment.start_at_utc, specialist_tz)}")

    details_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить запись", callback_data=f"client_appt:cancel:{appointment.appointment_id}")],
            [
                InlineKeyboardButton(
                    text="Перенести (скоро)",
                    callback_data=f"client_appt:reschedule:{appointment.appointment_id}",
                )
            ],
            [InlineKeyboardButton(text="Назад к списку", callback_data="client_appt:list")],
        ]
    )

    await callback.message.answer("\n".join(details_lines), reply_markup=details_keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("client_appt:cancel:"))
async def client_appointment_cancel_confirm_prompt(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
        return
    if callback.message is None:
        await callback.answer()
        return

    appointment_id_raw = callback.data.removeprefix("client_appt:cancel:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись не найдена", show_alert=True)
        return

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
                .where(Appointment.appointment_id == appointment_id)
                .where(Appointment.client_id == client.client_id)
                .where(Appointment.specialist_id == specialist_id)
            )
        ).scalar_one_or_none()

    if appointment is None:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    if appointment.booking_state != BookingState.confirmed:
        await callback.answer("Отмена доступна только для подтверждённой записи.", show_alert=True)
        return

    client_tz = await _get_client_tz(specialist_id=specialist_id, tg_user_id=callback.from_user.id)
    formatted_datetime = format_session_datetime(appointment.start_at_utc, client_tz)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, отменить",
                    callback_data=f"client_appt:cancel_confirm:{appointment.appointment_id}",
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data=f"client_appt:view:{appointment.appointment_id}")],
        ]
    )
    await callback.message.answer(f"Подтвердите отмену записи на {formatted_datetime}.", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("client_appt:cancel_confirm:"))
async def client_appointment_cancel_confirm(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_appt:cancel_confirm:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None:
            await callback.answer("Профиль клиента не найден. Нажмите /start.", show_alert=True)
            return
        if appointment is None:
            await callback.answer("Запись не найдена", show_alert=True)
            return

        if appointment.booking_state == BookingState.canceled_by_client:
            if callback.message is not None:
                await callback.message.answer("Запись уже отменена.")
                await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)
            await callback.answer()
            return

        if appointment.booking_state != BookingState.confirmed:
            await callback.answer("Отмена доступна только для подтверждённой записи.", show_alert=True)
            return

        min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
        try:
            await _validate_min_hours_policy(
                specialist_id=specialist_id,
                target_start_utc=appointment.start_at_utc,
            )
        except ValueError:
            if callback.message is not None:
                await callback.message.answer(
                    f"Отмена через бота недоступна менее чем за {min_hours} часов до начала. Напишите специалисту."
                )
            await callback.answer()
            return

        try:
            await _cancel_client_appointment(
                session=session,
                specialist_id=specialist_id,
                client=client,
                appointment=appointment,
                comment=None,
            )
        except Exception:
            logger.exception(
                "Failed to cancel appointment from client callback",
                extra={
                    "specialist_id": str(specialist_id),
                    "appointment_id": str(appointment.appointment_id),
                },
            )
            if hasattr(session, "rollback"):
                await session.rollback()
            if callback.message is not None:
                await callback.message.answer("Не удалось отменить запись. Попробуйте позже.")
            await callback.answer()
            return

        await session.commit()

    if callback.message is not None:
        await callback.message.answer("Запись отменена.")
        await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("client_rem:confirm:"))
async def client_reminder_confirm(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_rem:confirm:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await callback.answer("Запись неактуальна.", show_alert=True)
            return

        payload = {
            "appointment_id": str(appointment.appointment_id),
            "specialist_id": str(appointment.specialist_id),
            "client_id": str(appointment.client_id),
            "start_at_utc": appointment.start_at_utc.isoformat(),
        }
        await emit_outbox_domain_event(session, "appointment_client_confirmed", payload)
        await session.commit()

    if callback.message is not None:
        await callback.message.answer("Спасибо! Отметили, что вы придёте.")
    await callback.answer()


@router.callback_query(F.data.startswith("client_rem:cancel:"))
async def client_reminder_cancel_entry(callback, specialist_id) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_rem:cancel:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await callback.answer("Запись неактуальна.", show_alert=True)
            return
        min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
        try:
            await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=appointment.start_at_utc)
        except ValueError:
            await callback.answer(
                f"Отмена недоступна менее чем за {min_hours} часов до начала. Напишите специалисту.",
                show_alert=True,
            )
            return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оставить комментарий специалисту", callback_data=f"client_rem:cancel_comment:yes:{appointment_id}")],
            [InlineKeyboardButton(text="Без комментария", callback_data=f"client_rem:cancel_comment:no:{appointment_id}")],
        ]
    )
    await callback.message.answer("Хотите оставить комментарий специалисту?", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("client_rem:cancel_comment:yes:"))
async def client_reminder_cancel_comment_yes(callback, specialist_id, state: FSMContext) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_rem:cancel_comment:yes:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await callback.answer("Запись неактуальна.", show_alert=True)
            return
        min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
        try:
            await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=appointment.start_at_utc)
        except ValueError:
            await callback.answer(
                f"Отмена недоступна менее чем за {min_hours} часов до начала. Напишите специалисту.",
                show_alert=True,
            )
            return

    await state.set_state(ClientReminderCancelCommentState.waiting_for_text)
    await state.update_data(reminder_cancel_appointment_id=str(appointment_id), reminder_cancel_specialist_id=str(specialist_id))
    await callback.message.answer("Напишите комментарий одним сообщением (до 500 символов).")
    await callback.answer()


@router.message(ClientReminderCancelCommentState.waiting_for_text)
async def client_reminder_cancel_comment_text(message: Message, specialist_id, state: FSMContext) -> None:
    if message.from_user is None:
        await state.clear()
        return

    raw_text = (message.text or "").strip()
    if not raw_text:
        await message.answer("Комментарий не должен быть пустым.")
        return
    comment = raw_text[:500]
    logger.info(
        "client_reminder_cancel_comment_received request_id=%s specialist_id=%s tg_user_id=%s comment_len=%s",
        get_request_id(),
        specialist_id,
        message.from_user.id,
        len(comment),
    )

    state_data = await state.get_data()
    appointment_id_raw = state_data.get("reminder_cancel_appointment_id")
    if not appointment_id_raw:
        await state.clear()
        await message.answer("Запись неактуальна.")
        return

    appointment_id = UUID(str(appointment_id_raw))
    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=message.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await state.clear()
            await message.answer("Запись неактуальна.")
            return

        min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
        try:
            await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=appointment.start_at_utc)
        except ValueError:
            await state.clear()
            await message.answer(f"Отмена недоступна менее чем за {min_hours} часов до начала. Напишите специалисту.")
            return

        try:
            await _cancel_client_appointment(
                session=session,
                specialist_id=specialist_id,
                client=client,
                appointment=appointment,
                comment=comment,
            )
        except Exception:
            logger.exception(
                "Failed to cancel appointment from reminder comment flow",
                extra={"specialist_id": str(specialist_id), "appointment_id": str(appointment_id)},
            )
            if hasattr(session, "rollback"):
                await session.rollback()
            await state.clear()
            await message.answer("Не удалось отменить запись. Попробуйте позже.")
            return
        await session.commit()

    await state.clear()
    await message.answer("Запись отменена.")
    await _render_client_appointments(message, specialist_id, message.from_user.id)


@router.callback_query(F.data.startswith("client_rem:cancel_comment:no:"))
async def client_reminder_cancel_comment_no(callback, specialist_id, state: FSMContext) -> None:
    if callback.from_user is None:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_rem:cancel_comment:no:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await callback.answer("Запись неактуальна.", show_alert=True)
            return

        min_hours = await _resolve_cancel_window_hours(specialist_id=specialist_id)
        try:
            await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=appointment.start_at_utc)
        except ValueError:
            await callback.answer(
                f"Отмена недоступна менее чем за {min_hours} часов до начала. Напишите специалисту.",
                show_alert=True,
            )
            return

        try:
            await _cancel_client_appointment(
                session=session,
                specialist_id=specialist_id,
                client=client,
                appointment=appointment,
                comment=None,
            )
        except Exception:
            logger.exception(
                "Failed to cancel appointment from reminder no-comment flow",
                extra={"specialist_id": str(specialist_id), "appointment_id": str(appointment_id)},
            )
            if hasattr(session, "rollback"):
                await session.rollback()
            if callback.message is not None:
                await callback.message.answer("Не удалось отменить запись. Попробуйте позже.")
            await callback.answer()
            return
        await session.commit()

    await state.clear()
    if callback.message is not None:
        await callback.message.answer("Запись отменена.")
        await _render_client_appointments(callback.message, specialist_id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("client_rem:contact:"))
async def client_reminder_contact_specialist(callback, specialist_id) -> None:
    if callback.from_user is None:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    appointment_id_raw = callback.data.removeprefix("client_rem:contact:")
    try:
        appointment_id = UUID(appointment_id_raw)
    except ValueError:
        await callback.answer("Запись неактуальна.", show_alert=True)
        return

    async with async_session_factory() as session:
        client, appointment = await _load_client_and_appointment_for_callback(
            session=session,
            specialist_id=specialist_id,
            tg_user_id=callback.from_user.id,
            appointment_id=appointment_id,
        )
        if client is None or appointment is None or appointment.booking_state != BookingState.confirmed:
            await callback.answer("Запись неактуальна.", show_alert=True)
            return

        now_utc = datetime.now(timezone.utc)
        idempotency_key, bucket_start, bucket_end = _contact_idempotency_key(
            appointment_id=appointment.appointment_id,
            now_utc=now_utc,
        )
        recent_contact_events = (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.event_type == "appointment_client_contact_specialist")
                .where(OutboxEvent.created_at >= bucket_start)
                .where(OutboxEvent.created_at < bucket_end)
            )
        ).scalars().all()
        for existing in recent_contact_events:
            payload = existing.payload_json or {}
            if payload.get("idempotency_key") == idempotency_key:
                if callback.message is not None:
                    await callback.message.answer("Уже передали просьбу специалисту.")
                await callback.answer()
                return

        payload = {
            "appointment_id": str(appointment.appointment_id),
            "specialist_id": str(appointment.specialist_id),
            "client_id": str(appointment.client_id),
            "start_at_utc": appointment.start_at_utc.isoformat(),
            "idempotency_key": idempotency_key,
        }
        await emit_outbox_domain_event(session, "appointment_client_contact_specialist", payload)
        await session.commit()

    if callback.message is not None:
        await callback.message.answer("Передал специалисту просьбу написать вам.")
    await callback.answer()


@router.callback_query(F.data.startswith("client_appt:reschedule:"))
async def client_appointment_action_stub(callback) -> None:
    await callback.answer("Функция скоро появится.", show_alert=True)


@router.callback_query(F.data == "client_appt:menu")
async def client_my_appointments_to_menu(callback) -> None:
    await callback.answer()
    if callback.message is None:
        return
    await callback.message.answer("Возвращаю в меню.")
    await start_router.render_client_menu(
        callback.message,
        where="client_my_appointments_to_menu",
        bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
    )


@router.message(F.text == "Сменить часовой пояс")
async def client_change_timezone_button(
    message: Message,
    actor: str,
    specialist_id,
    state: FSMContext,
) -> None:
    if actor != "client" or message.from_user is None:
        return

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == message.from_user.id)
            )
        ).scalar_one_or_none()

    current_tz = client.client_timezone if client and client.client_timezone else "UTC"

    await state.set_state(ClientTimezoneState.waiting_for_timezone)

    await message.answer(
        f"Текущий часовой пояс: {current_tz}\n"
        "Выберите из списка или отправьте вручную (пример: Europe/Berlin).\n"
        "Страница: 1/3",
        reply_markup=build_timezone_keyboard(1, "client_tz", include_manual=False),
    )


@router.callback_query(F.data.startswith("client_tz:page:"))
async def client_tz_page_callback(callback: CallbackQuery, state: FSMContext, actor: str) -> None:
    if actor != "client":
        await callback.answer()
        return

    raw_page = (callback.data or "").removeprefix("client_tz:page:")
    try:
        page = int(raw_page)
    except ValueError:
        page = 1

    max_page = MAX_TZ_PAGE
    page = max(1, min(page, max_page))

    await state.set_state(ClientTimezoneState.waiting_for_timezone)

    text = (
        "Выберите из списка или отправьте вручную (пример: Europe/Berlin).\n"
        f"Страница: {page}/{max_page}"
    )

    if callback.message is not None:
        try:
            await callback.message.edit_text(text, reply_markup=build_timezone_keyboard(page, "client_tz", include_manual=False))
        except Exception:
            await callback.message.answer(text, reply_markup=build_timezone_keyboard(page, "client_tz", include_manual=False))

    await callback.answer()


@router.callback_query(F.data.startswith("client_tz:set:"))
async def client_tz_set_callback(callback: CallbackQuery, state: FSMContext, actor: str, specialist_id) -> None:
    if actor != "client":
        await callback.answer()
        return

    if callback.from_user is None:
        await callback.answer()
        return

    tz_name = (callback.data or "").removeprefix("client_tz:set:")
    if _validate_tz_name(tz_name) is None:
        await callback.answer("Неизвестный часовой пояс. Пример: Europe/Berlin", show_alert=True)
        return

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == callback.from_user.id)
            )
        ).scalar_one_or_none()
        if client is not None:
            client.client_timezone = tz_name
            client.timezone_source = ClientTimezoneSource.client_selected
            await session.commit()

    await state.clear()
    if callback.message is not None:
        await callback.message.answer(f"Готово. Теперь время будет показано в {tz_name}.")
        await start_router.render_client_menu(
            callback.message,
            where="client_tz_set_callback",
            specialist_id=specialist_id,
            bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
        )
    await callback.answer()


@router.callback_query(F.data == "client_tz:cancel")
async def client_tz_cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.answer("Отменено.")
        await start_router.render_client_menu(
            callback.message,
            where="client_tz_cancel_callback",
            bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
        )
    await callback.answer()


@router.message(ClientTimezoneState.waiting_for_timezone, F.text)
async def client_tz_text_input(message: Message, actor: str, specialist_id, state: FSMContext) -> None:
    if actor != "client" or message.from_user is None:
        return
    if (message.text or "").startswith("/"):
        return

    tz_name = _normalize_tz_input(message.text)
    if _validate_tz_name(tz_name) is None:
        await message.answer("Не удалось распознать часовой пояс. Пример: Europe/Berlin")
        return

    async with async_session_factory() as session:
        client = (
            await session.execute(
                select(Client)
                .where(Client.specialist_id == specialist_id)
                .where(Client.tg_user_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        if client is not None:
            client.client_timezone = tz_name
            client.timezone_source = ClientTimezoneSource.client_selected
            await session.commit()

    await state.clear()
    await message.answer(f"Готово. Теперь время будет показано в {tz_name}.")
    await start_router.render_client_menu(
        message,
        where="client_tz_text_input",
        specialist_id=specialist_id,
        bot_user_id=getattr(getattr(message, "bot", None), "id", None),
    )


@router.message(F.text == "🏠 В меню")
async def client_back_to_menu(message: Message, actor: str, state: FSMContext, specialist_id) -> None:
    if actor != "client":
        return
    await state.clear()
    await start_router.recover_client_entrypoint(
        message,
        specialist_id=specialist_id,
        where="client_back_to_menu",
        bot_user_id=getattr(getattr(message, "bot", None), "id", None),
    )


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
    )
    await start_router.render_client_menu(
        message,
        where="client_capture_display_name",
        specialist_id=specialist_id,
        bot_user_id=getattr(getattr(message, "bot", None), "id", None),
    )


@router.message(F.text)
async def client_unexpected_text_fallback(
    message: Message,
    actor: str,
    specialist_id,
    event_update: Update | None = None,
) -> None:
    if actor != "client":
        return
    text = message.text or ""
    if text.startswith("/"):
        return

    logger.info(
        "client_fallback_unexpected_text request_id=%s update_id=%s user_id=%s text=%r",
        get_request_id(),
        event_update.update_id if event_update else None,
        message.from_user.id if message.from_user else None,
        text,
    )
    await start_router.recover_client_entrypoint(
        message,
        specialist_id=specialist_id,
        where="client_unexpected_text_fallback",
        bot_user_id=getattr(getattr(message, "bot", None), "id", None),
    )


@router.callback_query()
async def client_unknown_callback_fallback(callback: CallbackQuery, actor: str, specialist_id) -> None:
    if actor != "client":
        return
    await callback.answer()
    if callback.message is not None:
        await start_router.recover_client_entrypoint(
            callback.message,
            specialist_id=specialist_id,
            where="client_unknown_callback_fallback",
            bot_user_id=getattr(getattr(callback, "bot", None), "id", None),
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
        await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=target_start_utc)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer("✅ Заглушка: booking допустим по правилу окна до начала слота.")


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
        await _validate_min_hours_policy(specialist_id=specialist_id, target_start_utc=target_start_utc)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await message.answer("✅ Заглушка: перенос допустим по правилу окна до начала слота.")
