from datetime import datetime, time, timezone
import logging
from typing import Sequence

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from sqlalchemy import select

from database import (
    Specialist,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    SpecialistProfile,
    WeeklyAvailability,
    async_session_factory,
)
from services.google_calendar import (
    create_and_cleanup_test_event,
    create_bot_calendar,
    list_calendars,
    resolve_tz_for_calendar_creation,
)
from services.specialist_defaults import (
    apply_specialist_defaults_if_missing,
    ALLOWED_SLOT_STEPS_MIN,
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
_ALLOWED_SLOT_STEPS_MIN = ALLOWED_SLOT_STEPS_MIN

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


class AvailabilityValidationError(ValueError):
    """Ошибка валидации интервала weekly availability."""


def _validate_interval_pair(*, start: time | None, end: time | None) -> None:
    if (start is None) ^ (end is None):
        raise AvailabilityValidationError("Interval start/end must be both NULL or both set.")
    if start is not None and end is not None and start >= end:
        raise AvailabilityValidationError("Interval start must be earlier than end.")



def _owner_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Изменить расписание", callback_data="owner_panel:change_schedule")],
            [InlineKeyboardButton(text="⏱️ Изменить длительность и буфер", callback_data="owner_panel:change_duration_buffer")],
            [InlineKeyboardButton(text="⚙️ Изменить лимиты (max/day, шаг слота)", callback_data="owner_panel:slot_params_menu")],
            [InlineKeyboardButton(text="🗓️ Сменить календарь", callback_data="owner_panel:calendar_menu")],
            [InlineKeyboardButton(text="🌍 Сменить TZ", callback_data="owner_panel:change_timezone")],
            [InlineKeyboardButton(text="👌 Оставить как есть", callback_data="owner_panel:keep")],
            [InlineKeyboardButton(text="♻️ Сбросить на дефолты", callback_data="owner_panel:apply_defaults")],
        ]
    )


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
        ]
    )


def _max_sessions_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for value in range(1, 11):
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
            if profile.slot_step_min not in _ALLOWED_SLOT_STEPS_MIN:
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

        if session_duration_min is not None:
            profile.session_duration_min = session_duration_min
        if session_buffer_min is not None:
            profile.session_buffer_min = session_buffer_min
        if max_sessions_per_day is not None:
            profile.max_sessions_per_day = max_sessions_per_day
        if slot_step_min is not None and slot_step_min in _ALLOWED_SLOT_STEPS_MIN:
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
        f"TZ: {calendar_settings.calendar_time_zone or '—'}\n"
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

    return not weekly_ready


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

    defaults_applied = await _ensure_owner_panel_defaults(
        specialist_id=specialist_id,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )

    if defaults_applied:
        await message.answer(
            "✅ Применены базовые настройки (их можно изменить): TZ, расписание (Пн–Пт, утро/день/вечер), "
            "длительность, буфер, лимиты."
        )

    profile, rows = await _load_profile_and_rows(specialist_id)
    calendar_settings = await _load_calendar_settings(specialist_id)
    if profile is None:
        logger.error("send_owner_panel: SpecialistProfile not found for specialist_id=%s", specialist_id)
        await message.answer(
            "⚠️ Профиль не найден. Вернитесь в master-бот и завершите онбординг заново."
        )
        return

    display_name = public_name or profile.public_name or "специалист"
    sample_day = next((row for row in rows if row.is_working), None)
    intervals_text = _format_intervals_for_ui(sample_day)

    text = (
        f"✅ Базовые настройки уже применены автоматически после онбординга, {display_name}.\n"
        "Хотите изменить их сейчас?\n\n"
        f"• Таймзона: {(profile.specialist_timezone or DEFAULT_TIMEZONE)}\n"
        f"• Рабочие дни: {_working_days(rows)}\n"
        f"• Интервалы (утро/день/вечер): {intervals_text}\n"
        f"• Длительность сессии: {(profile.session_duration_min or _DEFAULT_DURATION_MIN)} мин\n"
        f"• Буфер между сессиями: {(profile.session_buffer_min if profile.session_buffer_min is not None else _DEFAULT_BUFFER_MIN)} мин\n"
        f"• Шаг начала слотов: {(profile.slot_step_min or _DEFAULT_SLOT_STEP_MIN)} мин\n"
        f"• Окно отмены: {(profile.cancel_window_hours or _DEFAULT_CANCEL_WINDOW_HOURS)} ч\n"
        f"• Максимум сессий в день: {(profile.max_sessions_per_day or _DEFAULT_MAX_SESSIONS_PER_DAY)}\n\n"
        f"{_calendar_info_text(calendar_settings)}"
    )
    await message.answer(text, reply_markup=_owner_panel_keyboard())


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
    await send_owner_panel(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


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
    await send_owner_panel(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)


@router.callback_query(F.data == "owner_panel:apply_defaults")
async def owner_panel_apply_defaults(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    await _update_profile_settings(
        specialist_id=specialist_id,
        session_duration_min=_DEFAULT_DURATION_MIN,
        session_buffer_min=_DEFAULT_BUFFER_MIN,
        max_sessions_per_day=_DEFAULT_MAX_SESSIONS_PER_DAY,
        slot_step_min=_DEFAULT_SLOT_STEP_MIN,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )
    await _apply_weekly_defaults(
        specialist_id=specialist_id,
        working_days=set(DEFAULT_WORKING_DAYS),
        interval_1=_DEFAULT_WORKING_HOURS[0],
        interval_2=_DEFAULT_WORKING_HOURS[1],
        interval_3=_DEFAULT_WORKING_HOURS[2],
    )

    await callback.answer("Готово")
    await callback.message.answer(
        "✅ Применены базовые настройки (их можно изменить): TZ, расписание (Пн–Пт, утро/день/вечер), "
        "длительность, буфер, лимиты."
    )
    await send_owner_panel(
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
    await callback.message.answer(
        "Выберите действие с календарём:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🆕 Создать новый", callback_data="owner_cal:create")],
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
    await send_owner_panel(
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
    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_id)
        profile = await session.get(SpecialistProfile, specialist_id)

    if specialist is None or profile is None:
        await callback.message.answer("⚠️ Профиль специалиста не найден.")
        await send_owner_panel(
            callback.message,
            specialist_id=specialist_id,
            public_name=public_name,
            owner_tg_user_id=owner_tg_user_id,
        )
        return

    tz_for_create = await resolve_tz_for_calendar_creation(
        specialist_id=specialist.specialist_id,
        profile_tz=profile.specialist_timezone,
    )
    calendar = await create_bot_calendar(
        specialist.specialist_id,
        profile.public_name,
        tz_for_create,
    )
    calendar_id = calendar.get("id")
    calendar_summary = calendar.get("summary")
    if not calendar_id:
        await callback.message.answer("⚠️ Google не вернул ID календаря.")
        await send_owner_panel(
            callback.message,
            specialist_id=specialist_id,
            public_name=public_name,
            owner_tg_user_id=owner_tg_user_id,
        )
        return
    calendar_tz = (calendar.get("timeZone") or tz_for_create or "UTC").strip() or "UTC"

    await _upsert_calendar_settings(
        specialist_id=specialist.specialist_id,
        calendar_id=calendar_id,
        calendar_summary=calendar_summary,
        calendar_tz=calendar_tz,
        source=SpecialistCalendarSource.created,
    )

    async with async_session_factory() as session:
        await apply_specialist_defaults_if_missing(
            session,
            specialist.specialist_id,
            preferred_timezone=calendar_tz,
        )
        await session.commit()

    try:
        await create_and_cleanup_test_event(specialist.specialist_id, calendar_id, calendar_tz)
        await _upsert_calendar_settings(
            specialist_id=specialist.specialist_id,
            calendar_id=calendar_id,
            calendar_summary=calendar_summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.created,
            smoke_status="ok",
            smoke_error=None,
        )
        await callback.message.answer("✅ Новый календарь создан, интеграция успешно выполнена.")
    except Exception as exc:
        await _upsert_calendar_settings(
            specialist_id=specialist.specialist_id,
            calendar_id=calendar_id,
            calendar_summary=calendar_summary,
            calendar_tz=calendar_tz,
            source=SpecialistCalendarSource.created,
            smoke_status="failed",
            smoke_error=str(exc)[:255],
        )
        await callback.message.answer("⚠️ Календарь создан, но интеграция не завершена.")

    await send_owner_panel(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_cal:select")
async def owner_calendar_select(callback: CallbackQuery, specialist_id) -> None:
    await callback.answer()
    items = await list_calendars(specialist_id)
    if not items:
        await callback.message.answer("⚠️ В аккаунте Google не найдено доступных календарей.")
        return

    _CALENDAR_SELECTION_CACHE[callback.from_user.id] = items

    keyboard_rows = []
    for index, item in enumerate(items):
        title = item.get("summary") or f"Календарь {index + 1}"
        keyboard_rows.append(
            [InlineKeyboardButton(text=f"{index + 1}. {title}", callback_data=f"owner_cal:pick:{index}")]
        )
    keyboard_rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="owner_cal:back")])

    await callback.message.answer(
        "Выберите календарь:",
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
        await callback.message.answer("⚠️ Не удалось выбрать календарь.")
        return

    items = _CALENDAR_SELECTION_CACHE.get(callback.from_user.id) or []
    if pick_index < 0 or pick_index >= len(items):
        await callback.message.answer("⚠️ Список календарей устарел. Откройте выбор заново.")
        return

    item = items[pick_index]
    calendar_id = item.get("id")
    summary = item.get("summary")
    if not calendar_id:
        await callback.message.answer("⚠️ Выбранный календарь не содержит ID.")
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
        await callback.message.answer("✅ Календарь выбран, интеграция успешно выполнена.")
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
        await callback.message.answer("⚠️ Календарь сохранён, но интеграция не завершена.")

    _CALENDAR_SELECTION_CACHE.pop(callback.from_user.id, None)
    await send_owner_panel(
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
        await callback.message.answer("⚠️ Календарь не выбран. Сначала создайте или выберите календарь.")
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
        await callback.message.answer("✅ Интеграция успешно выполнена.")
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
        await callback.message.answer("❌ Интеграция не завершена.")

    await send_owner_panel(
        callback.message,
        specialist_id=specialist_id,
        public_name=public_name,
        owner_tg_user_id=owner_tg_user_id,
    )


@router.callback_query(F.data == "owner_panel:slot_params_menu")
async def owner_panel_slot_params_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Что хотите изменить?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Шаг слотов", callback_data="owner_panel:slot_step_menu")],
                [InlineKeyboardButton(text="Максимум сессий/день", callback_data="owner_panel:max_sessions_menu")],
            ]
        ),
    )


@router.callback_query(F.data == "owner_panel:max_sessions_menu")
async def owner_panel_max_sessions_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите максимум сессий в день:",
        reply_markup=_max_sessions_keyboard(),
    )


@router.callback_query(F.data.startswith("owner:slot_step:"))
async def owner_panel_set_slot_step(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    try:
        step_min = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный шаг", show_alert=True)
        return

    if step_min not in _ALLOWED_SLOT_STEPS_MIN:
        await callback.answer("Некорректный шаг", show_alert=True)
        return

    await _update_profile_settings(
        specialist_id=specialist_id,
        slot_step_min=step_min,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )

    await callback.answer()
    await callback.message.answer(f"Шаг начала слотов обновлён: {step_min} мин")
    await send_owner_panel(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)




@router.callback_query(F.data == "owner_panel:change_duration_buffer")
async def owner_panel_change_duration_buffer(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⏱️ Изменение длительности и буфера в разработке. Пока можно использовать мастер настроек."
    )


@router.callback_query(F.data == "owner_panel:change_timezone")
async def owner_panel_change_timezone(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🌍 Смена TZ в разработке. Пока используется TZ из профиля специалиста."
    )

@router.callback_query(F.data == "owner_panel:change_schedule")
async def owner_panel_change_schedule(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "📅 Изменение расписания в разработке. Пока можно использовать мастер настроек."
    )


@router.callback_query(F.data == "owner_panel:keep")
async def owner_panel_keep(callback: CallbackQuery) -> None:
    await callback.answer("Отлично")
    await callback.message.answer("👌 Оставили текущие настройки без изменений.")


@router.callback_query(F.data.startswith("owner:max_sessions:"))
async def owner_panel_set_max_sessions(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    try:
        max_sessions = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректное значение", show_alert=True)
        return

    if max_sessions < 1 or max_sessions > 10:
        await callback.answer("Некорректное значение", show_alert=True)
        return

    await _update_profile_settings(
        specialist_id=specialist_id,
        max_sessions_per_day=max_sessions,
        owner_tg_user_id=owner_tg_user_id,
        public_name=public_name,
    )

    await callback.answer()
    await callback.message.answer(f"Лимит сессий в день обновлён: {max_sessions}")
    await send_owner_panel(callback.message, specialist_id=specialist_id, public_name=public_name, owner_tg_user_id=owner_tg_user_id)
