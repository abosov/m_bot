from datetime import datetime, time, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging
from typing import Sequence
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from sqlalchemy import select

from database import (
    Specialist,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    SpecialistProfile,
    SpecialistPublicProfile,
    SpecialistWorkingHours,
    WeeklyAvailability,
    async_session_factory,
)
from handlers.personal_bot.ui.timezones import MAX_TZ_PAGE, build_timezone_keyboard
from handlers.personal_bot.routers.specialist.settings_view import build_specialist_settings_view
from services.google_calendar import (
    create_and_cleanup_test_event,
    list_calendars,
)
from services.specialist_schedule import (
    ValidationError as SpecialistScheduleValidationError,
    add_working_interval,
    delete_working_interval,
    get_specialist_schedule,
    update_limits,
    update_session_settings,
    update_specialist_timezone,
    reset_specialist_settings_to_default,
)
from services.weekly_availability import get_working_days, toggle_working_day
from services.working_intervals import (
    WorkingIntervalsValidationError,
    apply_interval_edit,
    ensure_default_working_intervals,
)
from services.working_intervals_repository import WorkingIntervalsRepository
from services.referrals import build_referral_link, count_active_referrals
from services.telegram.calendar_keyboard import format_calendar_button_text
from services.web_connect_links import build_profile_edit_url_for_specialist
from services.log_context import log_event
from services.specialist_defaults import (
    apply_specialist_defaults_if_missing,
    DEFAULT_BUFFER_MIN,
    DEFAULT_CANCEL_WINDOW_HOURS,
    DEFAULT_DURATION_MIN,
    DEFAULT_MAX_SESSIONS_PER_DAY,
    DEFAULT_SLOT_STEP_MIN,
    DEFAULT_TIMEZONE,
    DEFAULT_WORKING_DAYS,
    DEFAULT_WORKING_INTERVALS,
)

router = Router(name="personal_bot_specialist_owner_panel")
logger = logging.getLogger(__name__)

_CALENDAR_SELECTION_CACHE: dict[int, list[dict]] = {}

_DEFAULT_DURATION_MIN = DEFAULT_DURATION_MIN
_DEFAULT_BUFFER_MIN = DEFAULT_BUFFER_MIN
_DEFAULT_CANCEL_WINDOW_HOURS = DEFAULT_CANCEL_WINDOW_HOURS
_DEFAULT_MAX_SESSIONS_PER_DAY = DEFAULT_MAX_SESSIONS_PER_DAY
_DEFAULT_SLOT_STEP_MIN = DEFAULT_SLOT_STEP_MIN

_WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

_DEFAULT_WORKING_HOURS = DEFAULT_WORKING_INTERVALS

_PUBLIC_SLUG_RE = re.compile(r"^[A-Za-z0-9_]+$")


class AvailabilityValidationError(ValueError):
    """Ошибка валидации интервала weekly availability."""


class ScheduleEditStates(StatesGroup):
    choosing_weekday = State()
    menu = State()
    interval_menu = State()
    waiting_interval_start = State()
    waiting_interval_end = State()
    waiting_start_time = State()
    waiting_end_time = State()


class SessionSettingsStates(StatesGroup):
    waiting_duration = State()
    waiting_buffer = State()


class LimitsSettingsStates(StatesGroup):
    waiting_for_daily_limit = State()
    waiting_for_slot_step = State()


class TimezoneSettingsStates(StatesGroup):
    waiting_for_timezone = State()
    waiting_manual_timezone = State()


_NAV_CHAT_ID_KEY = "owner_panel_nav_chat_id"
_NAV_MESSAGE_ID_KEY = "owner_panel_nav_message_id"
_OWNER_TZ_PAGE_KEY = "owner_panel_tz_page"


def _validate_interval_pair(*, start: time | None, end: time | None) -> None:
    if (start is None) ^ (end is None):
        raise AvailabilityValidationError("Interval start/end must be both NULL or both set.")
    if start is not None and end is not None and start >= end:
        raise AvailabilityValidationError("Interval start must be earlier than end.")



def _slot_step_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="60", callback_data="owner:slot_step:60"),
                InlineKeyboardButton(text="30", callback_data="owner:slot_step:30"),
            ],
            [
                InlineKeyboardButton(text="15", callback_data="owner:slot_step:15"),
                InlineKeyboardButton(text="10", callback_data="owner:slot_step:10"),
            ],
            [InlineKeyboardButton(text="5", callback_data="owner:slot_step:5")],
        ]
    )




def _apply_defaults_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить", callback_data="owner_panel:apply_defaults:confirm")],
            [InlineKeyboardButton(text="Отмена", callback_data="owner_panel:apply_defaults:cancel")],
        ]
    )



_POPULAR_TIMEZONES = [
    "UTC",
    "Europe/Moscow",
    "Europe/Berlin",
    "Europe/London",
    "Asia/Dubai",
    "Asia/Almaty",
    "Asia/Tbilisi",
    "Asia/Yerevan",
    "Asia/Tashkent",
    "Asia/Bangkok",
    "Asia/Tokyo",
    "America/New_York",
]


def _timezone_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for tz_name in _POPULAR_TIMEZONES:
        row.append(InlineKeyboardButton(text=tz_name, callback_data=f"owner_tz:set:{tz_name}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✍️ Ввести вручную", callback_data="owner_tz:manual")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="owner_tz:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _save_specialist_timezone(
    *,
    message: Message,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
    timezone_name: str,
) -> None:
    try:
        updated = await update_specialist_timezone(specialist_id, timezone_name)
    except SpecialistScheduleValidationError as exc:
        await message.answer(
            f"⚠️ Не удалось сохранить timezone: {exc}.\n"
            "Выберите timezone из списка или введите вручную в формате Region/City.",
            reply_markup=_timezone_keyboard(),
        )
        await state.set_state(TimezoneSettingsStates.waiting_manual_timezone)
        return

    await state.clear()
    await message.answer(
        "✅ Часовой пояс специалиста сохранён\n"
        f"• Timezone: {updated['specialist_timezone']}\n\n"
        "ℹ️ Уже созданные события Google Calendar не изменяются.",
    )
    await send_owner_panel(
        message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


async def _remember_nav_message(state: FSMContext, message: Message) -> None:
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    message_id = getattr(message, "message_id", None)
    if isinstance(chat_id, int) and isinstance(message_id, int):
        await state.update_data(**{_NAV_CHAT_ID_KEY: chat_id, _NAV_MESSAGE_ID_KEY: message_id})


async def _edit_nav_message(
    bot,
    *,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def _edit_nav_message_from_state(
    message: Message,
    state: FSMContext,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    chat_id = data.get(_NAV_CHAT_ID_KEY)
    message_id = data.get(_NAV_MESSAGE_ID_KEY)
    if isinstance(chat_id, int) and isinstance(message_id, int):
        await _edit_nav_message(
            message.bot,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        return
    await message.answer(text, reply_markup=reply_markup)

def _max_sessions_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for value in range(1, 21):
        row.append(InlineKeyboardButton(text=str(value), callback_data=f"owner:max_sessions:{value}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _decision_keyboard(*, keep_data: str, change_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оставить как есть", callback_data=keep_data)],
            [InlineKeyboardButton(text="Изменить", callback_data=change_data)],
        ]
    )


def _format_time(value: time | None) -> str:
    return value.strftime("%H:%M") if value else "—"


def _working_days(rows: Sequence[WeeklyAvailability]) -> str:
    days = [_WEEKDAY_LABELS.get(row.weekday, str(row.weekday)) for row in rows if row.is_working]
    return ", ".join(days) if days else "не заданы"


def _has_configured_weekly(rows: Sequence[WeeklyAvailability]) -> bool:
    if not rows:
        return False

    for row in rows:
        if not row.is_working:
            continue
        if row.interval_1_start and row.interval_1_end:
            return True
        if row.interval_2_start and row.interval_2_end:
            return True
        if row.interval_3_start and row.interval_3_end:
            return True
    return False


def _iter_defined_intervals(row: WeeklyAvailability) -> list[tuple[time, time]]:
    intervals: list[tuple[time, time]] = []
    for start, end in (
        (row.interval_1_start, row.interval_1_end),
        (row.interval_2_start, row.interval_2_end),
        (row.interval_3_start, row.interval_3_end),
    ):
        _validate_interval_pair(start=start, end=end)
        if start is not None and end is not None:
            intervals.append((start, end))
    return intervals


def _format_intervals_for_ui(row: WeeklyAvailability | None) -> str:
    if row is None:
        return "09:00–12:00, 13:00–17:00, 17:00–21:00"

    intervals = _iter_defined_intervals(row)
    if not intervals:
        return "не заданы"
    return ", ".join(f"{_format_time(start)}–{_format_time(end)}" for start, end in intervals)


async def _ensure_profile_defaults(
    *,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> bool:
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        changed = False

        if profile is None:
            if owner_tg_user_id is None:
                return False
            profile = SpecialistProfile(
                specialist_id=specialist_id,
                public_name=public_name or "Специалист",
                owner_tg_user_id=owner_tg_user_id,
                owner_tg_username=None,
                specialist_timezone=DEFAULT_TIMEZONE,
                session_duration_min=_DEFAULT_DURATION_MIN,
                session_buffer_min=_DEFAULT_BUFFER_MIN,
                slot_step_min=_DEFAULT_SLOT_STEP_MIN,
                cancel_window_hours=_DEFAULT_CANCEL_WINDOW_HOURS,
                max_sessions_per_day=_DEFAULT_MAX_SESSIONS_PER_DAY,
            )
            session.add(profile)
            changed = True
        else:
            if not (profile.specialist_timezone or "").strip():
                profile.specialist_timezone = DEFAULT_TIMEZONE
                changed = True
            if profile.session_duration_min <= 0:
                profile.session_duration_min = _DEFAULT_DURATION_MIN
                changed = True
            if profile.session_buffer_min < 0:
                profile.session_buffer_min = _DEFAULT_BUFFER_MIN
                changed = True
            if profile.cancel_window_hours <= 0:
                profile.cancel_window_hours = _DEFAULT_CANCEL_WINDOW_HOURS
                changed = True
            if profile.max_sessions_per_day <= 0:
                profile.max_sessions_per_day = _DEFAULT_MAX_SESSIONS_PER_DAY
                changed = True
            if (
                profile.slot_step_min is None
                or profile.slot_step_min < 5
                or profile.slot_step_min > profile.session_duration_min
                or profile.slot_step_min % 5 != 0
            ):
                profile.slot_step_min = _DEFAULT_SLOT_STEP_MIN
                changed = True

        if changed:
            await session.commit()

    return True


async def _apply_weekly_defaults(
    *,
    specialist_id,
    working_days: set[int],
    interval_1: tuple[time, time] | None,
    interval_2: tuple[time, time] | None,
    interval_3: tuple[time, time] | None,
) -> None:
    _validate_interval_pair(start=interval_1[0] if interval_1 else None, end=interval_1[1] if interval_1 else None)
    _validate_interval_pair(start=interval_2[0] if interval_2 else None, end=interval_2[1] if interval_2 else None)
    _validate_interval_pair(start=interval_3[0] if interval_3 else None, end=interval_3[1] if interval_3 else None)

    async with async_session_factory() as session:
        existing = (
            await session.execute(
                select(WeeklyAvailability).where(WeeklyAvailability.specialist_id == specialist_id)
            )
        ).scalars().all()
        by_weekday = {row.weekday: row for row in existing}

        for weekday in range(7):
            row = by_weekday.get(weekday)
            if row is None:
                row = WeeklyAvailability(specialist_id=specialist_id, weekday=weekday)
                session.add(row)

            if weekday in working_days:
                row.is_working = True
                row.interval_1_start, row.interval_1_end = interval_1 if interval_1 else (None, None)
                row.interval_2_start, row.interval_2_end = interval_2 if interval_2 else (None, None)
                row.interval_3_start, row.interval_3_end = interval_3 if interval_3 else (None, None)
            else:
                row.is_working = False
                row.interval_1_start = None
                row.interval_1_end = None
                row.interval_2_start = None
                row.interval_2_end = None
                row.interval_3_start = None
                row.interval_3_end = None

        await session.commit()


async def _update_profile_settings(
    *,
    specialist_id,
    session_duration_min: int | None = None,
    session_buffer_min: int | None = None,
    max_sessions_per_day: int | None = None,
    slot_step_min: int | None = None,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    if not await _ensure_profile_defaults(
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    ):
        return

    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile is None:
            return

        next_duration = session_duration_min if session_duration_min is not None else profile.session_duration_min
        next_max_sessions = max_sessions_per_day if max_sessions_per_day is not None else profile.max_sessions_per_day
        next_slot_step = slot_step_min if slot_step_min is not None else profile.slot_step_min

        if next_max_sessions < 1 or next_max_sessions > 20:
            raise AvailabilityValidationError("max_sessions_per_day must be between 1 and 20")
        if next_slot_step < 5:
            raise AvailabilityValidationError("slot_step_minutes must be >= 5")
        if next_slot_step > next_duration:
            raise AvailabilityValidationError("slot_step_minutes must be <= session_duration")
        if next_slot_step % 5 != 0:
            raise AvailabilityValidationError("slot_step_minutes must be a multiple of 5")

        if session_duration_min is not None:
            profile.session_duration_min = session_duration_min
        if session_buffer_min is not None:
            profile.session_buffer_min = session_buffer_min
        if max_sessions_per_day is not None:
            profile.max_sessions_per_day = max_sessions_per_day
        if slot_step_min is not None:
            profile.slot_step_min = slot_step_min

        await session.commit()


async def _load_profile_and_rows(specialist_id):
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        rows = (
            await session.execute(
                select(WeeklyAvailability)
                .where(WeeklyAvailability.specialist_id == specialist_id)
                .order_by(WeeklyAvailability.weekday.asc())
            )
        ).scalars().all()
    return profile, rows


async def _load_calendar_settings(specialist_id):
    async with async_session_factory() as session:
        return await session.get(SpecialistCalendarSettings, specialist_id)


async def _upsert_calendar_settings(
    *,
    specialist_id,
    calendar_id: str,
    calendar_summary: str | None,
    calendar_tz: str | None,
    source: SpecialistCalendarSource,
    smoke_status: str | None = None,
    smoke_error: str | None = None,
) -> SpecialistCalendarSettings:
    async with async_session_factory() as session:
        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        now = datetime.now(timezone.utc)

        if settings is None:
            settings = SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                calendar_summary=calendar_summary,
                calendar_time_zone=calendar_tz,
                source=source,
            )
            session.add(settings)
        else:
            settings.calendar_id = calendar_id
            settings.calendar_summary = calendar_summary
            settings.calendar_time_zone = calendar_tz
            settings.source = source

        if smoke_status is not None:
            settings.last_smoke_test_status = smoke_status
            settings.last_smoke_test_error = smoke_error
            settings.last_smoke_test_at = now

        await session.commit()
        return settings


def _calendar_info_text(calendar_settings: SpecialistCalendarSettings | None) -> str:
    if calendar_settings is None:
        return "🗓 Календарь: Не подключён"

    return (
        "🗓 Календарь:\n"
        f"Название: {calendar_settings.calendar_summary or '—'}\n"
        f"Часовой пояс календаря (Google): {calendar_settings.calendar_time_zone or '—'}\n"
        f"Интеграция: {calendar_settings.last_smoke_test_status or '—'}"
    )


async def _ensure_owner_panel_defaults(
    *,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> bool:
    profile_ready = await _ensure_profile_defaults(
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    if not profile_ready:
        return False

    _, rows = await _load_profile_and_rows(specialist_id)
    weekly_ready = _has_configured_weekly(rows)
    if not weekly_ready:
        await _apply_weekly_defaults(
            specialist_id=specialist_id,
            working_days=set(DEFAULT_WORKING_DAYS),
            interval_1=_DEFAULT_WORKING_HOURS[0],
            interval_2=_DEFAULT_WORKING_HOURS[1],
            interval_3=_DEFAULT_WORKING_HOURS[2],
        )

    working_intervals_changed = await ensure_default_working_intervals(specialist_id)
    return (not weekly_ready) or working_intervals_changed




async def _load_referral_program_stats(specialist_id) -> tuple[str, int]:
    try:
        specialist_uuid = specialist_id if isinstance(specialist_id, UUID) else UUID(str(specialist_id))
    except (ValueError, TypeError):
        return "—", 0

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            return "—", 0
        referral_link = build_referral_link(specialist.referral_code)
        invited_count = await count_active_referrals(session, specialist_uuid)
        return referral_link, invited_count


async def _load_public_page_url_for_settings(specialist_id) -> str | None:
    async with async_session_factory() as session:
        public_profile = (
            await session.execute(
                select(SpecialistPublicProfile.public_slug, SpecialistPublicProfile.is_published)
                .where(SpecialistPublicProfile.specialist_id == specialist_id)
                .limit(1)
            )
        ).mappings().first()

    if not public_profile:
        return None

    if not bool(public_profile.get("is_published")):
        return None

    slug = (public_profile.get("public_slug") or "").strip()
    if not slug or not _PUBLIC_SLUG_RE.fullmatch(slug):
        return None

    return f"https://zumbot.ru/{slug}"


async def _build_owner_panel_view(
    *,
    specialist_id,
    public_name: str | None,
    owner_tg_user_id: int | None,
) -> tuple[str, InlineKeyboardMarkup] | None:
    profile, rows = await _load_profile_and_rows(specialist_id)
    calendar_settings = await _load_calendar_settings(specialist_id)
    working_intervals_by_idx = await WorkingIntervalsRepository().get_working_intervals(specialist_id)
    if profile is None:
        return None

    display_name = public_name or profile.public_name or "специалист"
    referral_link, invited_count = await _load_referral_program_stats(specialist_id)
    public_page_url = await _load_public_page_url_for_settings(specialist_id)
    text, keyboard = build_specialist_settings_view(
        profile=profile,
        rows=rows,
        calendar_settings=calendar_settings,
        keep_button_text=None,
        keep_callback_data=None,
        include_reset_button=True,
        working_intervals_by_idx=working_intervals_by_idx,
        public_page_url=public_page_url,
        referral_link=referral_link,
        referrals_count=invited_count,
    )
    text = (
        f"✅ Базовые настройки уже применены автоматически после онбординга, {display_name}.\n"
        "Хотите изменить их сейчас?\n\n"
        + text
    )
    return text, keyboard

async def send_owner_panel(
    message: Message,
    specialist_id,
    public_name: str | None,
    owner_tg_user_id: int | None = None,
) -> None:
    if specialist_id is None:
        logger.error("send_owner_panel called without specialist_id")
        await message.answer(
            "⚠️ Профиль специалиста не найден. Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    if owner_tg_user_id is None:
        logger.error("send_owner_panel called without owner_tg_user_id for specialist_id=%s", specialist_id)
        await message.answer(
            "⚠️ Не удалось определить Telegram-профиль владельца бота. "
            "Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    await _ensure_owner_panel_defaults(
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )

    panel_view = await _build_owner_panel_view(specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)
    if panel_view is None:
        logger.error("send_owner_panel: SpecialistProfile not found for specialist_id=%s", specialist_id)
        await message.answer(
            "⚠️ Профиль не найден. Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    text, keyboard = panel_view
    await message.answer(text, reply_markup=keyboard)


async def _render_owner_panel_inplace(
    message: Message,
    specialist_id,
    public_name: str | None,
    owner_tg_user_id: int | None = None,
) -> None:
    if specialist_id is None:
        logger.error("_render_owner_panel_inplace called without specialist_id")
        await message.edit_text(
            "⚠️ Профиль специалиста не найден. Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    if owner_tg_user_id is None:
        logger.error("_render_owner_panel_inplace called without owner_tg_user_id for specialist_id=%s", specialist_id)
        await message.edit_text(
            "⚠️ Не удалось определить Telegram-профиль владельца бота. "
            "Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    await _ensure_owner_panel_defaults(
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )

    panel_view = await _build_owner_panel_view(specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)
    if panel_view is None:
        logger.error("_render_owner_panel_inplace: SpecialistProfile not found for specialist_id=%s", specialist_id)
        await message.edit_text(
            "⚠️ Профиль не найден. Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    text, keyboard = panel_view
    # IMPORTANT: Settings menu must always re-render via edit_message to avoid message stacking
    await message.edit_text(text, reply_markup=keyboard)


async def _send_wizard_step_days(message: Message) -> None:
    await message.answer(
        "Шаг 1/4 — рабочие дни.\n"
        "Дефолт: Пн–Пт рабочие, Сб–Вс выходные.",
        reply_markup=_decision_keyboard(
            keep_data="owner_wizard:days:keep",
            change_data="owner_wizard:days:change",
        ),
    )


async def _send_wizard_step_intervals(message: Message) -> None:
    await message.answer(
        "Шаг 2/4 — интервалы по дню.\n"
        "Дефолт: утро 09:00–12:00, день 13:00–17:00, вечер 17:00–21:00.",
        reply_markup=_decision_keyboard(
            keep_data="owner_wizard:intervals:keep",
            change_data="owner_wizard:intervals:change",
        ),
    )


async def _send_wizard_step_duration_buffer(message: Message) -> None:
    await message.answer(
        "Шаг 3/4 — длительность и буфер.\n"
        "Дефолт: длительность 60 мин, буфер 10 мин.",
        reply_markup=_decision_keyboard(
            keep_data="owner_wizard:duration:keep",
            change_data="owner_wizard:duration:change",
        ),
    )


async def _send_wizard_step_limits(message: Message) -> None:
    await message.answer(
        "Шаг 4/4 — лимит сессий и шаг слотов.\n"
        "Дефолт: максимум 4 сессии в день, шаг слотов 15 мин.",
        reply_markup=_decision_keyboard(
            keep_data="owner_wizard:limits:keep",
            change_data="owner_wizard:limits:change",
        ),
    )


@router.callback_query(F.data == "owner_wizard:start")
async def owner_wizard_start(callback: CallbackQuery) -> None:
    await callback.answer()
    await _send_wizard_step_days(callback.message)


@router.callback_query(F.data == "owner_wizard:days:keep")
async def owner_wizard_days_keep(callback: CallbackQuery, specialist_id) -> None:
    await _apply_weekly_defaults(
        specialist_id=specialist_id,
        working_days=set(DEFAULT_WORKING_DAYS),
        interval_1=_DEFAULT_WORKING_HOURS[0],
        interval_2=_DEFAULT_WORKING_HOURS[1],
        interval_3=_DEFAULT_WORKING_HOURS[2],
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_intervals(callback.message)


@router.callback_query(F.data == "owner_wizard:days:change")
async def owner_wizard_days_change(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите рабочие дни:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Пн–Пт (рекомендуется)", callback_data="owner_wizard:days:set:weekdays")],
                [InlineKeyboardButton(text="Пн–Вс", callback_data="owner_wizard:days:set:all")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:days:set:"))
async def owner_wizard_days_set(callback: CallbackQuery, specialist_id) -> None:
    selection = (callback.data or "").split(":")[-1]
    if selection == "all":
        working_days = {0, 1, 2, 3, 4, 5, 6}
    else:
        working_days = {0, 1, 2, 3, 4}

    await _apply_weekly_defaults(
        specialist_id=specialist_id,
        working_days=working_days,
        interval_1=_DEFAULT_WORKING_HOURS[0],
        interval_2=_DEFAULT_WORKING_HOURS[1],
        interval_3=_DEFAULT_WORKING_HOURS[2],
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_intervals(callback.message)


@router.callback_query(F.data == "owner_wizard:intervals:keep")
async def owner_wizard_intervals_keep(callback: CallbackQuery, specialist_id) -> None:
    _, rows = await _load_profile_and_rows(specialist_id)
    working_days = {row.weekday for row in rows if row.is_working}
    if not working_days:
        working_days = {0, 1, 2, 3, 4}

    await _apply_weekly_defaults(
        specialist_id=specialist_id,
        working_days=working_days,
        interval_1=_DEFAULT_WORKING_HOURS[0],
        interval_2=_DEFAULT_WORKING_HOURS[1],
        interval_3=_DEFAULT_WORKING_HOURS[2],
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_duration_buffer(callback.message)


@router.callback_query(F.data == "owner_wizard:intervals:change")
async def owner_wizard_intervals_change(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Интервал «утро» 09:00–12:00 оставить включённым?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оставить", callback_data="owner_wizard:interval_set:morning:1")],
                [InlineKeyboardButton(text="Выключить", callback_data="owner_wizard:interval_set:morning:0")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:interval_set:morning:"))
async def owner_wizard_set_morning(callback: CallbackQuery) -> None:
    morning = (callback.data or "").split(":")[-1]
    await callback.answer()
    await callback.message.answer(
        "Интервал «день» 13:00–17:00 оставить включённым?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оставить", callback_data=f"owner_wizard:interval_set:day:{morning}:1")],
                [InlineKeyboardButton(text="Выключить", callback_data=f"owner_wizard:interval_set:day:{morning}:0")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:interval_set:day:"))
async def owner_wizard_set_day(callback: CallbackQuery) -> None:
    chunks = (callback.data or "").split(":")
    morning = chunks[-2]
    day = chunks[-1]
    await callback.answer()
    await callback.message.answer(
        "Интервал «вечер» 17:00–21:00 оставить включённым?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оставить", callback_data=f"owner_wizard:interval_finalize:{morning}:{day}:1")],
                [InlineKeyboardButton(text="Выключить", callback_data=f"owner_wizard:interval_finalize:{morning}:{day}:0")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:interval_finalize:"))
async def owner_wizard_intervals_finalize(callback: CallbackQuery, specialist_id) -> None:
    chunks = (callback.data or "").split(":")
    enabled = chunks[-3:]

    _, rows = await _load_profile_and_rows(specialist_id)
    working_days = {row.weekday for row in rows if row.is_working}
    if not working_days:
        working_days = {0, 1, 2, 3, 4}

    interval_1 = _DEFAULT_WORKING_HOURS[0] if enabled[0] == "1" else None
    interval_2 = _DEFAULT_WORKING_HOURS[1] if enabled[1] == "1" else None
    interval_3 = _DEFAULT_WORKING_HOURS[2] if enabled[2] == "1" else None

    await _apply_weekly_defaults(
        specialist_id=specialist_id,
        working_days=working_days,
        interval_1=interval_1,
        interval_2=interval_2,
        interval_3=interval_3,
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_duration_buffer(callback.message)


@router.callback_query(F.data == "owner_wizard:duration:keep")
async def owner_wizard_duration_keep(callback: CallbackQuery, specialist_id, owner_tg_user_id: int | None, public_name: str | None) -> None:
    await _update_profile_settings(
        specialist_id=specialist_id,
        session_duration_min=_DEFAULT_DURATION_MIN,
        session_buffer_min=_DEFAULT_BUFFER_MIN,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_limits(callback.message)


@router.callback_query(F.data == "owner_wizard:duration:change")
async def owner_wizard_duration_change(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите вариант длительности и буфера:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="60 / 10 (рекомендуется)", callback_data="owner_wizard:duration:set:60:10")],
                [InlineKeyboardButton(text="45 / 10", callback_data="owner_wizard:duration:set:45:10")],
                [InlineKeyboardButton(text="90 / 15", callback_data="owner_wizard:duration:set:90:15")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:duration:set:"))
async def owner_wizard_duration_set(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    chunks = (callback.data or "").split(":")
    duration_min = int(chunks[-2])
    buffer_min = int(chunks[-1])

    await _update_profile_settings(
        specialist_id=specialist_id,
        session_duration_min=duration_min,
        session_buffer_min=buffer_min,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    await callback.answer("Сохранено")
    await _send_wizard_step_limits(callback.message)


@router.callback_query(F.data == "owner_wizard:limits:keep")
async def owner_wizard_limits_keep(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await _update_profile_settings(
        specialist_id=specialist_id,
        max_sessions_per_day=_DEFAULT_MAX_SESSIONS_PER_DAY,
        slot_step_min=_DEFAULT_SLOT_STEP_MIN,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    await callback.answer("Готово")
    await callback.message.answer("✅ Мастер завершён. Базовые настройки сохранены.")
    await _render_owner_panel_inplace(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


@router.callback_query(F.data == "owner_wizard:limits:change")
async def owner_wizard_limits_change(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите максимум сессий/день и шаг слотов:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="4 / 15 (рекомендуется)", callback_data="owner_wizard:limits:set:4:15")],
                [InlineKeyboardButton(text="6 / 30", callback_data="owner_wizard:limits:set:6:30")],
                [InlineKeyboardButton(text="8 / 10", callback_data="owner_wizard:limits:set:8:10")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("owner_wizard:limits:set:"))
async def owner_wizard_limits_set(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    chunks = (callback.data or "").split(":")
    max_sessions_per_day = int(chunks[-2])
    slot_step_min = int(chunks[-1])

    await _update_profile_settings(
        specialist_id=specialist_id,
        max_sessions_per_day=max_sessions_per_day,
        slot_step_min=slot_step_min,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    await callback.answer("Готово")
    await callback.message.answer("✅ Мастер завершён. Базовые настройки сохранены.")
    await _render_owner_panel_inplace(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)




@router.callback_query(F.data == "owner_panel:profile_edit_link")
async def owner_panel_profile_edit_link(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
) -> None:
    if owner_tg_user_id is None or callback.from_user is None or callback.from_user.id != owner_tg_user_id:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    async with async_session_factory() as session:
        try:
            profile_edit_url = await build_profile_edit_url_for_specialist(
                session=session,
                specialist_id=specialist_id,
                tg_user_id=owner_tg_user_id,
            )
            await session.commit()
        except ValueError:
            logger.warning("Profile edit URL is unavailable due to PUBLIC_SITE_URL configuration")
            await callback.answer("Ссылка временно недоступна", show_alert=True)
            return

    await callback.answer()
    await callback.message.answer(
        "Откройте редактор профиля по свежей ссылке.\n"
        "Ссылка одноразовая и действует ограниченное время.",
        parse_mode=None,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Открыть редактор профиля", url=profile_edit_url)]]
        ),
    )
    logger.info(
        "event=owner_profile_edit_link_generated specialist_id=%s tg_user_id=%s path=%s",
        specialist_id,
        owner_tg_user_id,
        "/profile/edit",
    )

@router.callback_query(F.data == "owner_panel:apply_defaults")
async def owner_panel_apply_defaults(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Вы уверены, что хотите сбросить настройки?",
        reply_markup=_apply_defaults_confirmation_keyboard(),
    )


@router.callback_query(F.data == "owner_panel:apply_defaults:confirm")
async def owner_panel_apply_defaults_confirm(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await reset_specialist_settings_to_default(specialist_id)

    await callback.answer("Готово")
    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_panel:apply_defaults:cancel")
async def owner_panel_apply_defaults_cancel(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await callback.answer("Отменено")
    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )



@router.callback_query(F.data == "owner_panel:slot_step_menu")
async def owner_panel_slot_step_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите шаг начала слотов (в минутах):",
        reply_markup=_slot_step_keyboard(),
    )


@router.callback_query(F.data == "owner_panel:calendar_menu")
async def owner_panel_calendar_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "Выберите действие с календарём:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📂 Выбрать существующий", callback_data="owner_cal:select")],
                [InlineKeyboardButton(text="🔁 Проверить доступ", callback_data="owner_cal:smoke")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="owner_cal:back")],
            ]
        ),
    )


@router.callback_query(F.data == "owner_cal:back")
async def owner_calendar_back(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await callback.answer()
    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_cal:create")
async def owner_calendar_create(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "ℹ️ Сейчас Zumbot подключается только к уже существующему календарю Google.\n"
        "Если нужен отдельный календарь — создайте его вручную в Google Calendar, затем выберите в боте.\n\n"
        "Выберите действие с календарём:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📂 Выбрать существующий", callback_data="owner_cal:select")],
                [InlineKeyboardButton(text="🔁 Проверить доступ", callback_data="owner_cal:smoke")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="owner_cal:back")],
            ]
        ),
    )


@router.callback_query(F.data == "owner_cal:select")
@router.callback_query(F.data == "owner_cal:refresh")
async def owner_calendar_select(callback: CallbackQuery, specialist_id) -> None:
    await callback.answer()
    items = await list_calendars(specialist_id)
    if not items:
        await callback.message.edit_text("⚠️ В аккаунте Google не найдено доступных календарей.")
        return

    _CALENDAR_SELECTION_CACHE[callback.from_user.id] = items

    keyboard_rows = [[InlineKeyboardButton(text="🔄 Обновить список", callback_data="owner_cal:refresh")]]
    for index, item in enumerate(items):
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text=format_calendar_button_text(item),
                    callback_data=f"owner_cal:pick:{index}",
                )
            ]
        )
    keyboard_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="owner_cal:back")])

    await callback.message.edit_text(
        "Выберите календарь\n\nФормат: Название и часовой пояс календаря.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows),
    )


@router.callback_query(F.data.startswith("owner_cal:pick:"))
async def owner_calendar_pick(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await callback.answer()

    try:
        pick_index = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("⚠️ Не удалось выбрать календарь.", show_alert=True)
        return

    items = _CALENDAR_SELECTION_CACHE.get(callback.from_user.id) or []
    if pick_index < 0 or pick_index >= len(items):
        await callback.answer("⚠️ Список календарей устарел. Откройте выбор заново.", show_alert=True)
        return

    item = items[pick_index]
    calendar_id = item.get("id")
    summary = item.get("summary")
    if not calendar_id:
        await callback.answer("⚠️ Выбранный календарь не содержит ID.", show_alert=True)
        return
    calendar_tz = item.get("timeZone") or "UTC"

    await _upsert_calendar_settings(
        specialist_id=specialist_id,
        calendar_id=calendar_id,
        calendar_summary=summary,
        calendar_tz=calendar_tz,
        source=SpecialistCalendarSource.selected,
    )

    try:
        await create_and_cleanup_test_event(specialist_id, calendar_id, calendar_tz)
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=calendar_id,
            calendar_summary=summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.selected,
            smoke_status="ok",
            smoke_error=None,
        )
        await callback.answer("✅ Календарь выбран, интеграция успешно выполнена.")
    except Exception as exc:
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=calendar_id,
            calendar_summary=summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.selected,
            smoke_status="failed",
            smoke_error=str(exc)[:255],
        )
        await callback.answer("⚠️ Календарь сохранён, но интеграция не завершена.")

    _CALENDAR_SELECTION_CACHE.pop(callback.from_user.id, None)
    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_cal:smoke")
async def owner_calendar_smoke(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await callback.answer()
    settings = await _load_calendar_settings(specialist_id)
    if settings is None or not settings.calendar_id:
        await callback.answer("⚠️ Календарь не выбран. Сначала выберите календарь.", show_alert=True)
        return

    try:
        await create_and_cleanup_test_event(
            specialist_id,
            settings.calendar_id,
            settings.calendar_time_zone or "UTC",
        )
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            calendar_summary=settings.calendar_summary,
            calendar_tz=settings.calendar_time_zone,
            source=settings.source,
            smoke_status="ok",
            smoke_error=None,
        )
        await callback.answer("✅ Интеграция успешно выполнена.")
    except Exception as exc:
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            calendar_summary=settings.calendar_summary,
            calendar_tz=settings.calendar_time_zone,
            source=settings.source,
            smoke_status="failed",
            smoke_error=str(exc)[:255],
        )
        await callback.answer("❌ Интеграция не завершена.")

    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_panel:slot_params_menu")
async def owner_panel_slot_params_menu(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    await state.set_state(LimitsSettingsStates.waiting_for_daily_limit)
    await state.update_data(limits_max_sessions_candidate=None)
    await _remember_nav_message(state, callback.message)
    profile, _ = await _load_profile_and_rows(specialist_id)
    max_sessions = profile.max_sessions_per_day if profile is not None else _DEFAULT_MAX_SESSIONS_PER_DAY
    slot_step = profile.slot_step_min if profile is not None else _DEFAULT_SLOT_STEP_MIN
    await callback.answer()
    await callback.message.edit_text(
        "✅ Лимиты сохранены\n"
        f"• Максимум сессий в день: {max_sessions}\n"
        f"• Шаг слота: {slot_step} мин\n\n"
        "⚙️ Введите максимум сессий в день (1..20)."
    )


@router.message(LimitsSettingsStates.waiting_for_daily_limit)
async def owner_panel_receive_max_sessions(message: Message, state: FSMContext, specialist_id) -> None:
    try:
        max_sessions = int((message.text or "").strip())
    except ValueError:
        await message.answer("⚠️ Максимум сессий должен быть целым числом.\n\n⚙️ Введите максимум сессий в день (1..20).")
        return

    if max_sessions < 1 or max_sessions > 20:
        await message.answer("⚠️ Максимум сессий должен быть в диапазоне 1..20.\n\n⚙️ Введите максимум сессий в день (1..20).")
        return

    await state.update_data(limits_max_sessions_candidate=max_sessions)
    await state.set_state(LimitsSettingsStates.waiting_for_slot_step)
    await message.answer("⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50).")


@router.message(LimitsSettingsStates.waiting_for_slot_step)
async def owner_panel_receive_slot_step(
    message: Message,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    try:
        slot_step = int((message.text or "").strip())
    except ValueError:
        await message.answer(
            "⚠️ Шаг слота должен быть целым числом.\n\n"
            "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
        )
        return

    data = await state.get_data()
    max_sessions = data.get("limits_max_sessions_candidate")
    if not isinstance(max_sessions, int):
        await state.set_state(LimitsSettingsStates.waiting_for_daily_limit)
        await message.answer("⚠️ Не найден максимум сессий.\n\n⚙️ Введите максимум сессий в день (1..20).")
        return

    if slot_step < 5:
        await message.answer(
            "⚠️ Шаг слота должен быть не меньше 5 минут.\n\n"
            "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
        )
        return
    if slot_step % 5 != 0:
        await message.answer(
            "⚠️ Шаг слота должен быть кратен 5 минутам.\n\n"
            "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
        )
        return
    if slot_step > 50:
        await message.answer(
            "⚠️ Шаг слота должен быть не больше 50 минут.\n\n"
            "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
        )
        return

    try:
        updated = await update_limits(specialist_id, max_per_day=max_sessions, slot_step=slot_step)
    except SpecialistScheduleValidationError as exc:
        await message.answer(
            f"⚠️ Не удалось сохранить лимиты: {exc}.\n\n"
            "⚙️ Введите шаг слота в минутах (минимум 5, кратно 5, максимум 50)."
        )
        return

    await state.clear()
    await message.answer(
        "✅ Лимиты сохранены\n"
        f"• Максимум сессий в день: {updated['max_sessions_per_day']}\n"
        f"• Шаг слота: {updated['slot_step_min']} мин"
    )
    await send_owner_panel(message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)



@router.callback_query(F.data == "owner_panel:change_duration_buffer")
async def owner_panel_change_duration_buffer(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SessionSettingsStates.waiting_duration)
    await state.update_data(session_duration_candidate=None)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await callback.message.edit_text(
        "⏱️ Введите длительность сессии в минутах (15..240, кратно 5)."
    )


@router.message(SessionSettingsStates.waiting_duration)
async def owner_panel_receive_session_duration(message: Message, state: FSMContext, specialist_id) -> None:
    try:
        duration = int((message.text or "").strip())
    except ValueError:
        await message.answer("⚠️ Длительность должна быть целым числом минут. Попробуйте ещё раз.")
        return

    try:
        _validate_session_settings_input(duration=duration, buffer=0)
    except SpecialistScheduleValidationError as exc:
        await message.answer(f"⚠️ Некорректная длительность: {exc}. Попробуйте ещё раз.")
        return

    await state.update_data(session_duration_candidate=duration, specialist_id=specialist_id)
    await state.set_state(SessionSettingsStates.waiting_buffer)
    await message.answer("⏱️ Введите буфер между сессиями в минутах (0..120).")


@router.message(SessionSettingsStates.waiting_buffer)
async def owner_panel_receive_session_buffer(
    message: Message,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    try:
        buffer_min = int((message.text or "").strip())
    except ValueError:
        await message.answer("⚠️ Буфер должен быть целым числом минут. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    duration = data.get("session_duration_candidate")
    if not isinstance(duration, int):
        await state.set_state(SessionSettingsStates.waiting_duration)
        await message.answer("⚠️ Не найдена длительность. Введите длительность заново.")
        return

    try:
        updated = await update_session_settings(specialist_id, duration=duration, buffer=buffer_min)
    except SpecialistScheduleValidationError as exc:
        await message.answer(f"⚠️ Некорректный буфер: {exc}. Попробуйте ещё раз.")
        return

    await state.clear()
    await message.answer(
        "✅ Настройки сессии сохранены\n"
        f"• Длительность: {updated['session_duration_min']} мин\n"
        f"• Буфер: {updated['session_buffer_min']} мин"
    )
    await send_owner_panel(message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


@router.callback_query(F.data == "owner_panel:change_timezone")
async def owner_panel_change_timezone(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await state.set_state(TimezoneSettingsStates.waiting_for_timezone)
    await state.update_data(**{_OWNER_TZ_PAGE_KEY: 1})
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await _edit_nav_message_from_state(
        callback.message,
        state,
        text=(
            "🌍 Выберите часовой пояс специалиста из популярных или введите вручную в формате Region/City "
            "(например, Europe/Berlin).\n\n"
            "ℹ️ Смена timezone не изменяет уже созданные события Google Calendar.\n"
            "Страница: 1/3"
        ),
        reply_markup=build_timezone_keyboard(1, "owner_tz", include_cancel=False),
    )




@router.callback_query(F.data.startswith("owner_tz:page:"))
async def owner_panel_timezone_page(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return

    raw_page = (callback.data or "").removeprefix("owner_tz:page:")
    try:
        page = int(raw_page)
    except ValueError:
        page = 1

    page = max(1, min(page, MAX_TZ_PAGE))
    await state.set_state(TimezoneSettingsStates.waiting_for_timezone)
    await state.update_data(**{_OWNER_TZ_PAGE_KEY: page})
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await _edit_nav_message_from_state(
        callback.message,
        state,
        text=(
            "🌍 Выберите часовой пояс специалиста из популярных или введите вручную в формате Region/City "
            "(например, Europe/Berlin).\n\n"
            "ℹ️ Смена timezone не изменяет уже созданные события Google Calendar.\n"
            f"Страница: {page}/{MAX_TZ_PAGE}"
        ),
        reply_markup=build_timezone_keyboard(page, "owner_tz", include_cancel=False),
    )

@router.callback_query(F.data == "owner_tz:manual")
async def owner_panel_timezone_manual(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TimezoneSettingsStates.waiting_manual_timezone)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await callback.message.edit_text("✍️ Введите timezone вручную в формате Region/City, например: Europe/Berlin")


@router.callback_query(F.data == "owner_tz:back")
async def owner_panel_timezone_back(
    callback: CallbackQuery,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await state.clear()
    await callback.answer()
    await _render_owner_panel_inplace(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


@router.callback_query(F.data.startswith("owner_tz:set:"))
async def owner_panel_timezone_set(
    callback: CallbackQuery,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    timezone_name = (callback.data or "").split("owner_tz:set:", 1)[-1].strip()

    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        data = await state.get_data()
        page = data.get(_OWNER_TZ_PAGE_KEY, 1)
        if not isinstance(page, int):
            page = 1
        page = max(1, min(page, MAX_TZ_PAGE))
        await state.set_state(TimezoneSettingsStates.waiting_for_timezone)
        await state.update_data(**{_OWNER_TZ_PAGE_KEY: page})
        await _remember_nav_message(state, callback.message)
        await callback.answer()
        await _edit_nav_message_from_state(
            callback.message,
            state,
            text=(
                f"⚠️ Не удалось сохранить timezone: timezone does not exist: {timezone_name}.\n"
                "Выберите timezone из списка.\n\n"
                "ℹ️ Смена timezone не изменяет уже созданные события Google Calendar.\n"
                f"Страница: {page}/{MAX_TZ_PAGE}"
            ),
            reply_markup=build_timezone_keyboard(page, "owner_tz", include_cancel=False),
        )
        return

    try:
        updated = await update_specialist_timezone(specialist_id, timezone_name)
    except SpecialistScheduleValidationError as exc:
        data = await state.get_data()
        page = data.get(_OWNER_TZ_PAGE_KEY, 1)
        if not isinstance(page, int):
            page = 1
        page = max(1, min(page, MAX_TZ_PAGE))
        await state.set_state(TimezoneSettingsStates.waiting_for_timezone)
        await state.update_data(**{_OWNER_TZ_PAGE_KEY: page})
        await _remember_nav_message(state, callback.message)
        await callback.answer()
        await _edit_nav_message_from_state(
            callback.message,
            state,
            text=(
                f"⚠️ Не удалось сохранить timezone: {exc}.\n"
                "Выберите timezone из списка.\n\n"
                "ℹ️ Смена timezone не изменяет уже созданные события Google Calendar.\n"
                f"Страница: {page}/{MAX_TZ_PAGE}"
            ),
            reply_markup=build_timezone_keyboard(page, "owner_tz", include_cancel=False),
        )
        return

    await callback.answer("✅ Часовой пояс специалиста сохранён")
    await state.clear()
    await _render_owner_panel_inplace(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.message(TimezoneSettingsStates.waiting_manual_timezone)
async def owner_panel_timezone_manual_input(
    message: Message,
    state: FSMContext,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    timezone_name = (message.text or "").strip()
    await _save_specialist_timezone(
        message=message,
        state=state,
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
        timezone_name=timezone_name,
    )

def build_weekday_button_text(weekday: int, working_days: set[int]) -> str:
    label = _WEEKDAY_LABELS.get(weekday, str(weekday))
    if weekday in working_days:
        return f"✅ {label}"
    return label


def _schedule_weekday_keyboard(working_days: set[int]) -> InlineKeyboardMarkup:
    def _day_button(weekday: int) -> InlineKeyboardButton:
        label = build_weekday_button_text(weekday, working_days)
        return InlineKeyboardButton(text=label, callback_data=f"schedule:toggle_day:{weekday}")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_day_button(0), _day_button(1)],
            [_day_button(2), _day_button(3)],
            [_day_button(4), _day_button(5)],
            [_day_button(6)],
            [InlineKeyboardButton(text="⏰ Интервалы", callback_data="schedule:intervals_menu")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule:back_owner")],
        ]
    )






async def _edit_or_send_schedule_picker(
    callback: CallbackQuery,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> Message:
    return await callback.message.edit_text(text, reply_markup=reply_markup)


async def _render_weekday_picker(callback: CallbackQuery, *, specialist_id) -> None:
    await _edit_or_send_schedule_picker(
        callback,
        text="📅 Настройка расписания\n\nВыберите рабочие дни недели:",
        reply_markup=_schedule_weekday_keyboard(await get_working_days(specialist_id)),
    )


def _schedule_menu_keyboard(weekday: int, intervals: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Добавить", callback_data=f"schedule:add:{weekday}")],
        [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"schedule:delete_menu:{weekday}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule:pick_day")],
    ]
    if not intervals:
        rows[1][0] = InlineKeyboardButton(text="🗑️ Удалить (нет интервалов)", callback_data="schedule:noop")
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _weekday_label(weekday: int) -> str:
    return _WEEKDAY_LABELS.get(weekday, str(weekday))


async def _send_schedule_day_menu(message: Message, specialist_id, weekday: int) -> None:
    schedule = await get_specialist_schedule(specialist_id)
    intervals = schedule.get(weekday, [])
    if intervals:
        intervals_text = "\n".join(f"• {it['start']}–{it['end']}" for it in intervals)
    else:
        intervals_text = "• интервалов нет"
    await message.edit_text(
        f"📅 Настройка расписания — {_weekday_label(weekday)}\n\n"
        f"Текущие интервалы:\n{intervals_text}\n\n"
        "Выберите действие:",
        reply_markup=_schedule_menu_keyboard(weekday, intervals),
    )


def _format_min_to_hhmm(value: int | None) -> str:
    if value is None:
        return "—"
    hour, minute = divmod(value, 60)
    return f"{hour:02d}:{minute:02d}"


def _format_interval_pair_min(pair: tuple[int | None, int | None]) -> str:
    start_min, end_min = pair
    if start_min is None or end_min is None:
        return "—"
    return f"{_format_min_to_hhmm(start_min)}–{_format_min_to_hhmm(end_min)}"


def _interval_short_warning(*, pair: tuple[int | None, int | None], required_min: int) -> str:
    start_min, end_min = pair
    if start_min is None or end_min is None:
        return ""
    if (end_min - start_min) >= required_min:
        return ""
    return f" ⚠️ Слоты недоступны: окно короче {required_min} мин (текущей длительности сессии)."


def _schedule_intervals_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Интервал 1", callback_data="schedule:interval:1")],
            [InlineKeyboardButton(text="Интервал 2", callback_data="schedule:interval:2")],
            [InlineKeyboardButton(text="Интервал 3", callback_data="schedule:interval:3")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule:back_to_weekdays")],
        ]
    )


def _schedule_interval_actions_keyboard(idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить начало", callback_data=f"schedule:interval_start:{idx}")],
            [InlineKeyboardButton(text="Изменить конец", callback_data=f"schedule:interval_end:{idx}")],
            [InlineKeyboardButton(text="Выключить интервал", callback_data=f"schedule:interval_disable:{idx}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule:intervals_menu")],
        ]
    )


async def _render_intervals_menu(message: Message, specialist_id) -> None:
    await ensure_default_working_intervals(specialist_id)
    repository = WorkingIntervalsRepository()
    intervals = await repository.get_working_intervals(specialist_id)
    required_min = await _get_required_interval_min(specialist_id)

    await message.edit_text(
        _intervals_overview_text(intervals, required_min=required_min),
        reply_markup=_schedule_intervals_keyboard(),
    )


async def _render_interval_actions_menu(message: Message, specialist_id, idx: int) -> None:
    await ensure_default_working_intervals(specialist_id)
    repository = WorkingIntervalsRepository()
    intervals = await repository.get_working_intervals(specialist_id)
    value_text = _format_interval_pair_min(intervals[idx])

    await message.edit_text(
        _interval_actions_text(idx=idx, value_text=value_text),
        reply_markup=_schedule_interval_actions_keyboard(idx),
    )


def _interval_actions_text(*, idx: int, value_text: str) -> str:
    return (
        "📅 Настройка расписания и интервалов\n\n"
        f"Интервал {idx}: {value_text}\n\n"
        "Выберите действие:"
    )


async def _get_required_interval_min(specialist_id) -> int:
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)

    # В текущей модели слоты внутри окна считаются по session_duration_min,
    # buffer учитывается отдельно как разрыв между слотами/занятостью.
    return profile.session_duration_min if profile is not None else _DEFAULT_DURATION_MIN


def _intervals_overview_text(
    intervals: dict[int, tuple[int | None, int | None]],
    *,
    required_min: int,
    note: str | None = None,
) -> str:
    rows = [
        f"Интервал 1: {_format_interval_pair_min(intervals[1])}{_interval_short_warning(pair=intervals[1], required_min=required_min)}",
        f"Интервал 2: {_format_interval_pair_min(intervals[2])}{_interval_short_warning(pair=intervals[2], required_min=required_min)}",
        f"Интервал 3: {_format_interval_pair_min(intervals[3])}{_interval_short_warning(pair=intervals[3], required_min=required_min)}",
    ]
    text = (
        "📅 Настройка расписания и интервалов\n\n"
        + "\n".join(rows)
        + "\n\n"
        "Выберите интервал:"
    )
    if not note:
        return text
    return f"{text}\n\n{note}"


def _build_overlap_note(
    *,
    before: dict[int, tuple[int | None, int | None]],
    after: dict[int, tuple[int | None, int | None]],
    edited_idx: int,
) -> str | None:
    disabled: list[int] = []
    for idx in (1, 2, 3):
        if idx == edited_idx:
            continue
        b_start, b_end = before[idx]
        a_start, a_end = after[idx]
        was_active = b_start is not None and b_end is not None
        is_active = a_start is not None and a_end is not None
        if was_active and not is_active:
            disabled.append(idx)

    if not disabled:
        return None

    if len(disabled) == 1:
        return (
            f"ℹ️ Интервал {disabled[0]} выключен из-за перекрытия "
            f"после изменения интервала {edited_idx}."
        )

    listed = ", ".join(str(idx) for idx in disabled)
    return f"ℹ️ Интервалы {listed} выключены из-за перекрытия после изменения интервала {edited_idx}."


@router.callback_query(F.data == "owner_panel:change_schedule")
async def owner_panel_change_schedule(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    await state.set_state(ScheduleEditStates.choosing_weekday)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await _render_weekday_picker(callback, specialist_id=specialist_id)


@router.callback_query(F.data.startswith("schedule:interval:"))
async def schedule_interval_select(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    raw_idx = (callback.data or "").split(":")[-1]
    try:
        idx = int(raw_idx)
    except ValueError:
        await callback.answer("Некорректный интервал", show_alert=True)
        return
    if idx not in {1, 2, 3}:
        await callback.answer("Некорректный интервал", show_alert=True)
        return
    await state.update_data(schedule_interval_idx=idx)
    await state.set_state(ScheduleEditStates.interval_menu)
    await callback.answer()
    await _render_interval_actions_menu(callback.message, specialist_id, idx)


@router.callback_query(F.data == "schedule:intervals_menu")
async def schedule_intervals_menu(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    await state.set_state(ScheduleEditStates.menu)
    await callback.answer()
    await _render_intervals_menu(callback.message, specialist_id)


@router.callback_query(F.data.startswith("schedule:interval_disable:"))
async def schedule_interval_disable(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    raw_idx = (callback.data or "").split(":")[-1]
    try:
        idx = int(raw_idx)
    except ValueError:
        await callback.answer("Некорректный интервал", show_alert=True)
        return
    if idx not in {1, 2, 3}:
        await callback.answer("Некорректный интервал", show_alert=True)
        return

    await apply_interval_edit(
        specialist_id=specialist_id,
        idx=idx,
        new_start_min=None,
        new_end_min=None,
        action="disable",
    )
    await state.update_data(schedule_interval_idx=idx)
    await state.set_state(ScheduleEditStates.interval_menu)
    await callback.answer("Интервал выключен")
    await _render_interval_actions_menu(callback.message, specialist_id, idx)


@router.callback_query(F.data.startswith("schedule:interval_start:"))
async def schedule_interval_start_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    raw_idx = (callback.data or "").split(":")[-1]
    try:
        idx = int(raw_idx)
    except ValueError:
        await callback.answer("Некорректный интервал", show_alert=True)
        return
    if idx not in {1, 2, 3}:
        await callback.answer("Некорректный интервал", show_alert=True)
        return

    await state.update_data(schedule_interval_idx=idx)
    await state.set_state(ScheduleEditStates.waiting_interval_start)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await callback.message.edit_text(f"✍️ Интервал {idx}: введите новое начало в формате HH:MM.")


@router.callback_query(F.data.startswith("schedule:interval_end:"))
async def schedule_interval_end_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    raw_idx = (callback.data or "").split(":")[-1]
    try:
        idx = int(raw_idx)
    except ValueError:
        await callback.answer("Некорректный интервал", show_alert=True)
        return
    if idx not in {1, 2, 3}:
        await callback.answer("Некорректный интервал", show_alert=True)
        return

    await state.update_data(schedule_interval_idx=idx)
    await state.set_state(ScheduleEditStates.waiting_interval_end)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await callback.message.edit_text(f"✍️ Интервал {idx}: введите новое окончание в формате HH:MM.")


@router.callback_query(F.data == "schedule:pick_day")
async def schedule_pick_day(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    await state.set_state(ScheduleEditStates.choosing_weekday)
    await callback.answer()
    await _render_weekday_picker(callback, specialist_id=specialist_id)




@router.callback_query(F.data.startswith("schedule:toggle_day:"))
async def schedule_toggle_day(callback: CallbackQuery, specialist_id) -> None:
    try:
        weekday = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный день", show_alert=True)
        return

    working_days = await toggle_working_day(specialist_id, weekday)
    await callback.message.edit_text(
        "📅 Настройка расписания\n\nВыберите рабочие дни недели:",
        reply_markup=_schedule_weekday_keyboard(working_days),
    )
    await callback.answer()


@router.callback_query(F.data == "schedule:back_to_weekdays")
async def schedule_back_to_weekdays(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    await state.set_state(ScheduleEditStates.choosing_weekday)
    await callback.answer()
    await _render_weekday_picker(callback, specialist_id=specialist_id)


@router.callback_query(F.data == "schedule:back_owner")
async def schedule_back_owner(callback: CallbackQuery, state: FSMContext, specialist_id, owner_tg_user_id: int | None, public_name: str | None) -> None:
    await state.clear()
    await callback.answer()
    await _render_owner_panel_inplace(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


@router.callback_query(F.data.startswith("schedule:day:"))
async def schedule_select_day(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    try:
        weekday = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный день", show_alert=True)
        return
    await state.update_data(schedule_weekday=weekday)
    await state.set_state(ScheduleEditStates.menu)
    await callback.answer()
    await _send_schedule_day_menu(callback.message, specialist_id, weekday)


@router.callback_query(F.data.startswith("schedule:add:"))
async def schedule_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        weekday = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный день", show_alert=True)
        return
    await state.update_data(schedule_weekday=weekday)
    await state.set_state(ScheduleEditStates.waiting_start_time)
    await _remember_nav_message(state, callback.message)
    await callback.answer()
    await callback.message.edit_text(
        f"✍️ {_weekday_label(weekday)}: введите время начала в формате HH:MM (например, 09:00)."
    )




def _validate_session_settings_input(duration: int, buffer: int) -> None:
    if duration < 15 or duration > 240:
        raise SpecialistScheduleValidationError("session_duration must be between 15 and 240 minutes")
    if duration % 5 != 0:
        raise SpecialistScheduleValidationError("session_duration must be a multiple of 5 minutes")
    if buffer < 0 or buffer > 120:
        raise SpecialistScheduleValidationError("buffer_minutes must be between 0 and 120 minutes")

def _parse_hhmm(value: str) -> time | None:
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        return time(hour=hour, minute=minute)
    except Exception:
        return None


def _time_to_min(value: time) -> int:
    return value.hour * 60 + value.minute


@router.message(ScheduleEditStates.waiting_interval_start)
async def schedule_interval_receive_start(message: Message, state: FSMContext, specialist_id) -> None:
    start_time = _parse_hhmm(message.text or "")
    if start_time is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ Неверный формат времени. Используйте HH:MM, например 09:00.")
        return

    data = await state.get_data()
    idx = int(data.get("schedule_interval_idx", 0))
    if idx not in {1, 2, 3}:
        await state.set_state(ScheduleEditStates.menu)
        await _edit_nav_message_from_state(message, state, text="⚠️ Интервал не выбран. Вернитесь в меню интервалов.")
        return

    repository = WorkingIntervalsRepository()
    intervals = await repository.get_working_intervals(specialist_id)
    _, current_end = intervals[idx]
    if current_end is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ У интервала нет конца. Сначала задайте конец.")
        return

    new_start_min = _time_to_min(start_time)
    if new_start_min >= current_end:
        await _edit_nav_message_from_state(
            message,
            state,
            text=(
                "⚠️ Начало должно быть раньше конца. "
                f"Текущий конец: {_format_min_to_hhmm(current_end)}."
            ),
        )
        return

    before_intervals = dict(intervals)
    try:
        updated_intervals = await apply_interval_edit(
            specialist_id=specialist_id,
            idx=idx,
            new_start_min=new_start_min,
            new_end_min=current_end,
            action="set",
        )
    except WorkingIntervalsValidationError as exc:
        await _edit_nav_message_from_state(message, state, text=f"⚠️ Интервал не сохранён: {exc}")
        return

    await state.set_state(ScheduleEditStates.menu)
    overlap_note = _build_overlap_note(before=before_intervals, after=updated_intervals, edited_idx=idx)
    await _edit_nav_message_from_state(
        message,
        state,
        text=_intervals_overview_text(
            updated_intervals,
            required_min=await _get_required_interval_min(specialist_id),
            note=overlap_note,
        ),
        reply_markup=_schedule_intervals_keyboard(),
    )


@router.message(ScheduleEditStates.waiting_interval_end)
async def schedule_interval_receive_end(message: Message, state: FSMContext, specialist_id) -> None:
    end_time = _parse_hhmm(message.text or "")
    if end_time is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ Неверный формат времени. Используйте HH:MM, например 18:00.")
        return

    data = await state.get_data()
    idx = int(data.get("schedule_interval_idx", 0))
    if idx not in {1, 2, 3}:
        await state.set_state(ScheduleEditStates.menu)
        await _edit_nav_message_from_state(message, state, text="⚠️ Интервал не выбран. Вернитесь в меню интервалов.")
        return

    repository = WorkingIntervalsRepository()
    intervals = await repository.get_working_intervals(specialist_id)
    current_start, _ = intervals[idx]
    if current_start is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ У интервала нет начала. Сначала задайте начало.")
        return

    new_end_min = _time_to_min(end_time)
    if current_start >= new_end_min:
        await _edit_nav_message_from_state(
            message,
            state,
            text=(
                "⚠️ Конец должен быть позже начала. "
                f"Текущее начало: {_format_min_to_hhmm(current_start)}."
            ),
        )
        return

    before_intervals = dict(intervals)
    try:
        updated_intervals = await apply_interval_edit(
            specialist_id=specialist_id,
            idx=idx,
            new_start_min=current_start,
            new_end_min=new_end_min,
            action="set",
        )
    except WorkingIntervalsValidationError as exc:
        await _edit_nav_message_from_state(message, state, text=f"⚠️ Интервал не сохранён: {exc}")
        return

    await state.set_state(ScheduleEditStates.menu)
    overlap_note = _build_overlap_note(before=before_intervals, after=updated_intervals, edited_idx=idx)
    await _edit_nav_message_from_state(
        message,
        state,
        text=_intervals_overview_text(
            updated_intervals,
            required_min=await _get_required_interval_min(specialist_id),
            note=overlap_note,
        ),
        reply_markup=_schedule_intervals_keyboard(),
    )


@router.message(ScheduleEditStates.waiting_start_time)
async def schedule_add_receive_start(message: Message, state: FSMContext) -> None:
    start_time = _parse_hhmm(message.text or "")
    if start_time is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ Неверный формат времени. Используйте HH:MM, например 09:00.")
        return
    await state.update_data(schedule_start_time=start_time.strftime("%H:%M"))
    await state.set_state(ScheduleEditStates.waiting_end_time)
    await _edit_nav_message_from_state(message, state, text="✍️ Теперь введите время окончания в формате HH:MM (например, 18:00).")


@router.message(ScheduleEditStates.waiting_end_time)
async def schedule_add_receive_end(message: Message, state: FSMContext, specialist_id) -> None:
    end_time = _parse_hhmm(message.text or "")
    if end_time is None:
        await _edit_nav_message_from_state(message, state, text="⚠️ Неверный формат времени. Используйте HH:MM, например 18:00.")
        return

    data = await state.get_data()
    weekday = int(data.get("schedule_weekday", 0))
    start_time_raw = str(data.get("schedule_start_time", ""))
    start_time = _parse_hhmm(start_time_raw)
    if start_time is None:
        await state.set_state(ScheduleEditStates.waiting_start_time)
        await _edit_nav_message_from_state(message, state, text="⚠️ Не удалось прочитать время начала. Введите время начала заново (HH:MM).")
        return

    try:
        await add_working_interval(specialist_id, weekday, start_time, end_time)
    except SpecialistScheduleValidationError as exc:
        await _edit_nav_message_from_state(message, state, text=f"⚠️ Интервал не сохранён: {exc}\n✍️ Введите новое время начала в формате HH:MM.")
        await state.set_state(ScheduleEditStates.waiting_start_time)
        return

    await state.set_state(ScheduleEditStates.menu)
    await _send_schedule_day_menu(message, specialist_id, weekday)


@router.callback_query(F.data.startswith("schedule:delete_menu:"))
async def schedule_delete_menu(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    try:
        weekday = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный день", show_alert=True)
        return

    schedule = await get_specialist_schedule(specialist_id)
    intervals = schedule.get(weekday, [])
    if not intervals:
        await callback.answer("Нет интервалов для удаления", show_alert=True)
        return

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(SpecialistWorkingHours).where(
                    SpecialistWorkingHours.specialist_id == specialist_id,
                    SpecialistWorkingHours.weekday == weekday,
                ).order_by(SpecialistWorkingHours.start_time)
            )
        ).scalars().all()

    kb_rows = [[InlineKeyboardButton(text=f"🗑️ {row.start_time.strftime('%H:%M')}–{row.end_time.strftime('%H:%M')}", callback_data=f"schedule:delete:{row.id}")] for row in rows]
    kb_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"schedule:day:{weekday}")])
    await state.update_data(schedule_weekday=weekday)
    await callback.answer()
    await callback.message.edit_text(
        f"🗑️ {_weekday_label(weekday)}: выберите интервал для удаления.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )


@router.callback_query(F.data.startswith("schedule:delete:"))
async def schedule_delete_interval(callback: CallbackQuery, state: FSMContext, specialist_id) -> None:
    raw_id = (callback.data or "").split(":")[-1]
    try:
        interval_id = uuid.UUID(raw_id)
    except ValueError:
        await callback.answer("Некорректный интервал", show_alert=True)
        return

    data = await state.get_data()
    weekday = int(data.get("schedule_weekday", 0))

    try:
        await delete_working_interval(interval_id, specialist_id)
    except SpecialistScheduleValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.answer("Удалено")
    await _send_schedule_day_menu(callback.message, specialist_id, weekday)


@router.callback_query(F.data == "schedule:noop")
async def schedule_noop(callback: CallbackQuery) -> None:
    await callback.answer("Нет интервалов")
