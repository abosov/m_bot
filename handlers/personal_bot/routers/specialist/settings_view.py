from __future__ import annotations

from datetime import time
from typing import Sequence

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


def _format_time(value: time | None) -> str:
    return value.strftime("%H:%M") if value else "—"


def _working_days(rows: Sequence) -> str:
    days = [_WEEKDAY_LABELS.get(row.weekday, str(row.weekday)) for row in rows if row.is_working]
    return ", ".join(days) if days else "не заданы"


def _format_intervals_for_ui(row) -> str:
    if row is None:
        return "не заданы"

    intervals = []
    for start, end in (
        (row.interval_1_start, row.interval_1_end),
        (row.interval_2_start, row.interval_2_end),
        (row.interval_3_start, row.interval_3_end),
    ):
        if start is not None and end is not None and start < end:
            intervals.append((start, end))
    if not intervals:
        return "не заданы"
    return ", ".join(f"{_format_time(start)}–{_format_time(end)}" for start, end in intervals)


def build_specialist_settings_view(
    *,
    profile,
    rows: Sequence,
    calendar_settings,
    keep_button_text: str | None,
    keep_callback_data: str | None,
    include_reset_button: bool,
    later_button: tuple[str, str] | None = None,
) -> tuple[str, InlineKeyboardMarkup]:
    calendar_summary = "не выбран"
    calendar_time_zone = "—"
    smoke_status = "unknown"
    if calendar_settings is not None and getattr(calendar_settings, "calendar_id", None):
        calendar_summary = calendar_settings.calendar_summary or "не выбран"
        calendar_time_zone = calendar_settings.calendar_time_zone or "—"
        smoke_status = getattr(calendar_settings, "last_smoke_test_status", None) or "unknown"

    specialist_timezone = (profile.specialist_timezone or "UTC")
    sample_day = next((row for row in rows if row.is_working), None)
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
        f"• Окно отмены: {profile.cancel_window_hours} ч\n\n"
        f"Часовой пояс специалиста:\n• {specialist_timezone}\n\n"
        "Расписание:\n"
        f"• Рабочие дни: {_working_days(rows)}\n"
        f"• Интервалы: {_format_intervals_for_ui(sample_day)}"
    )

    keyboard_rows = [
        [InlineKeyboardButton(text="📅 Изменить расписание и интервалы", callback_data="owner_panel:change_schedule")],
        [InlineKeyboardButton(text="⏱️ Изменить длительность и буфер", callback_data="owner_panel:change_duration_buffer")],
        [InlineKeyboardButton(text="⚙️ Изменить лимиты (max/day, шаг слота)", callback_data="owner_panel:slot_params_menu")],
        [InlineKeyboardButton(text="🗓️ Сменить календарь", callback_data="owner_panel:calendar_menu")],
        [InlineKeyboardButton(text="🌍 Сменить часовой пояс специалиста", callback_data="owner_panel:change_timezone")],
    ]
    if keep_button_text is not None and keep_callback_data is not None:
        keyboard_rows.append([InlineKeyboardButton(text=keep_button_text, callback_data=keep_callback_data)])
    if include_reset_button:
        keyboard_rows.append([InlineKeyboardButton(text="♻️ Сбросить на дефолты", callback_data="owner_panel:apply_defaults")])
    if later_button is not None:
        later_text, later_callback = later_button
        keyboard_rows.append([InlineKeyboardButton(text=later_text, callback_data=later_callback)])

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
