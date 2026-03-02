from __future__ import annotations

from typing import Mapping, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


_WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

_TARIFF_PLAN_LABELS = {
    "free": "Free",
    "start": "Start",
    "pro": "Pro",
    "team": "Team",
}


def _format_minutes(value: int) -> str:
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"


def _working_days(rows: Sequence) -> str:
    days = [_WEEKDAY_LABELS.get(row.weekday, str(row.weekday)) for row in rows if row.is_working]
    return ", ".join(days) if days else "не заданы"


def _format_tariff_plan(profile) -> str:
    plan_raw = getattr(profile, "tariff_plan", "start")
    plan_value = getattr(plan_raw, "value", plan_raw)
    return _TARIFF_PLAN_LABELS.get(str(plan_value), str(plan_value).upper())


def _format_intervals_for_ui(intervals_by_idx: Mapping[int, tuple[int | None, int | None]] | None) -> str:
    if not intervals_by_idx:
        return "—"

    intervals = []
    for idx in (1, 2, 3):
        start, end = intervals_by_idx.get(idx, (None, None))
        if start is not None and end is not None and 0 <= start < end <= 1440:
            intervals.append((start, end))

    if not intervals:
        return "—"

    return ", ".join(f"{_format_minutes(start)}–{_format_minutes(end)}" for start, end in intervals)


def build_specialist_settings_view(
    *,
    profile,
    rows: Sequence,
    calendar_settings,
    keep_button_text: str | None,
    keep_callback_data: str | None,
    include_reset_button: bool,
    working_intervals_by_idx: Mapping[int, tuple[int | None, int | None]] | None = None,
    later_button: tuple[str, str] | None = None,
    referral_link: str | None = None,
    referrals_count: int = 0,
) -> tuple[str, InlineKeyboardMarkup]:
    calendar_summary = "не выбран"
    calendar_time_zone = "—"
    smoke_status = "unknown"
    if calendar_settings is not None and getattr(calendar_settings, "calendar_id", None):
        calendar_summary = calendar_settings.calendar_summary or "не выбран"
        calendar_time_zone = calendar_settings.calendar_time_zone or "—"
        smoke_status = getattr(calendar_settings, "last_smoke_test_status", None) or "unknown"

    specialist_timezone = (profile.specialist_timezone or "UTC")
    text = (
        "Календарь:\n"
        f"• Название: {calendar_summary}\n"
        f"• Часовой пояс календаря (Google): {calendar_time_zone}\n"
        f"• Интеграция: {smoke_status}\n\n"
        "Параметры записи:\n"
        f"• Длительность: {profile.session_duration_min} мин\n"
        f"• Буфер: {profile.session_buffer_min} мин\n"
        f"• Шаг слота: {profile.slot_step_min} мин\n"
        f"• Макс. сессий в день: {profile.max_sessions_per_day}\n"
        f"• Окно отмены: {profile.cancel_window_hours} ч\n"
        f"• Тариф: {_format_tariff_plan(profile)}\n\n"
        f"Часовой пояс специалиста:\n• {specialist_timezone}\n\n"
        "Расписание:\n"
        f"• Рабочие дни: {_working_days(rows)}\n"
        f"• Интервалы: {_format_intervals_for_ui(working_intervals_by_idx)}"
    )

    keyboard_rows = [
        [InlineKeyboardButton(text="📅 Сменить календарь", callback_data="owner_panel:calendar_menu")],
        [InlineKeyboardButton(text="⏱️ Изменить длительность и буфер", callback_data="owner_panel:change_duration_buffer")],
        [InlineKeyboardButton(text="⚙️ Изменить лимиты (max/day, шаг слота)", callback_data="owner_panel:slot_params_menu")],
        [InlineKeyboardButton(text="🌍 Сменить часовой пояс специалиста", callback_data="owner_panel:change_timezone")],
        [InlineKeyboardButton(text="📅 Изменить расписание и интервалы", callback_data="owner_panel:change_schedule")],
    ]
    if keep_button_text is not None and keep_callback_data is not None:
        keyboard_rows.append([InlineKeyboardButton(text=keep_button_text, callback_data=keep_callback_data)])
    if include_reset_button:
        keyboard_rows.append([InlineKeyboardButton(text="♻️ Сбросить на дефолты", callback_data="owner_panel:apply_defaults")])
    if later_button is not None:
        later_text, later_callback = later_button
        keyboard_rows.append([InlineKeyboardButton(text=later_text, callback_data=later_callback)])

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
