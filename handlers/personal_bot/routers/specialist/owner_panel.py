from datetime import time
from typing import Sequence

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from sqlalchemy import select

from database import SpecialistProfile, WeeklyAvailability, async_session_factory

router = Router(name="personal_bot_specialist_owner_panel")

_DEFAULT_DURATION_MIN = 60
_DEFAULT_BUFFER_MIN = 10
_DEFAULT_CANCEL_WINDOW_HOURS = 12
_DEFAULT_MAX_SESSIONS_PER_DAY = 4
_DEFAULT_SLOT_STEP_MIN = 15
_ALLOWED_SLOT_STEPS_MIN = {60, 30, 15, 10}

_WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

_DEFAULT_WORKING_HOURS = [
    (time(9, 0), time(12, 0)),
    (time(13, 0), time(17, 0)),
    (time(17, 0), time(21, 0)),
]


def _owner_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Применить настройки по умолчанию", callback_data="owner_panel:apply_defaults")],
            [InlineKeyboardButton(text="Шаг слотов", callback_data="owner_panel:slot_step_menu")],
            [InlineKeyboardButton(text="🛠 Настроить вручную", callback_data="owner_panel:manual")],
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="owner_panel:skip")],
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


def _format_time(value: time | None) -> str:
    return value.strftime("%H:%M") if value else "—"


def _working_days(rows: Sequence[WeeklyAvailability]) -> str:
    days = [_WEEKDAY_LABELS.get(row.weekday, str(row.weekday)) for row in rows if row.is_working]
    return ", ".join(days) if days else "не заданы"


async def send_owner_panel(message: Message, specialist_id, public_name: str | None) -> None:
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        rows = (
            await session.execute(
                select(WeeklyAvailability)
                .where(WeeklyAvailability.specialist_id == specialist_id)
                .order_by(WeeklyAvailability.weekday.asc())
            )
        ).scalars().all()

    display_name = public_name or (profile.public_name if profile else "специалист")
    sample_day = next((row for row in rows if row.is_working), None)

    if sample_day:
        intervals_text = (
            f"{_format_time(sample_day.interval_1_start)}–{_format_time(sample_day.interval_1_end)}, "
            f"{_format_time(sample_day.interval_2_start)}–{_format_time(sample_day.interval_2_end)}, "
            f"{_format_time(sample_day.interval_3_start)}–{_format_time(sample_day.interval_3_end)}"
        )
    else:
        intervals_text = "09:00–12:00, 13:00–17:00, 17:00–21:00"

    text = (
        f"⚙️ Базовые настройки, {display_name}.\n\n"
        f"• Рабочие дни: {_working_days(rows)}\n"
        f"• Интервалы (утро/день/вечер): {intervals_text}\n"
        f"• Длительность сессии: {(profile.session_duration_min if profile else _DEFAULT_DURATION_MIN)} мин\n"
        f"• Буфер между сессиями: {(profile.session_buffer_min if profile else _DEFAULT_BUFFER_MIN)} мин\n"
        f"• Шаг начала слотов: {(profile.slot_step_min if profile else _DEFAULT_SLOT_STEP_MIN)} мин\n"
        f"• Окно отмены: {(profile.cancel_window_hours if profile else _DEFAULT_CANCEL_WINDOW_HOURS)} ч\n"
        f"• Максимум сессий в день: {(profile.max_sessions_per_day if profile else _DEFAULT_MAX_SESSIONS_PER_DAY)}\n\n"
        "Правило записи: бронирование и изменение доступны только на следующий день и только до 21:00 предыдущего дня по вашему времени.\n\n"
        "Можно быстро применить рекомендуемые дефолты."
    )
    await message.answer(text, reply_markup=_owner_panel_keyboard())


@router.callback_query(F.data == "owner_panel:apply_defaults")
async def owner_panel_apply_defaults(
    callback: CallbackQuery,
    specialist_id,
    owner_tg_user_id: int | None,
    public_name: str | None,
) -> None:
    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile is None and owner_tg_user_id is not None:
            profile = SpecialistProfile(
                specialist_id=specialist_id,
                public_name=public_name or "Специалист",
                owner_tg_user_id=owner_tg_user_id,
                owner_tg_username=None,
                specialist_timezone="UTC",
                session_duration_min=_DEFAULT_DURATION_MIN,
                session_buffer_min=_DEFAULT_BUFFER_MIN,
                slot_step_min=_DEFAULT_SLOT_STEP_MIN,
                cancel_window_hours=_DEFAULT_CANCEL_WINDOW_HOURS,
                max_sessions_per_day=_DEFAULT_MAX_SESSIONS_PER_DAY,
            )
            session.add(profile)
        elif profile:
            profile.session_duration_min = _DEFAULT_DURATION_MIN
            if profile.session_buffer_min == 0:
                profile.session_buffer_min = _DEFAULT_BUFFER_MIN
            if profile.cancel_window_hours <= 0:
                profile.cancel_window_hours = _DEFAULT_CANCEL_WINDOW_HOURS
            if profile.max_sessions_per_day <= 0:
                profile.max_sessions_per_day = _DEFAULT_MAX_SESSIONS_PER_DAY
            if profile.slot_step_min not in _ALLOWED_SLOT_STEPS_MIN:
                profile.slot_step_min = _DEFAULT_SLOT_STEP_MIN

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

            if weekday <= 4:
                row.is_working = True
                row.interval_1_start, row.interval_1_end = _DEFAULT_WORKING_HOURS[0]
                row.interval_2_start, row.interval_2_end = _DEFAULT_WORKING_HOURS[1]
                row.interval_3_start, row.interval_3_end = _DEFAULT_WORKING_HOURS[2]
            else:
                row.is_working = False
                row.interval_1_start = None
                row.interval_1_end = None
                row.interval_2_start = None
                row.interval_2_end = None
                row.interval_3_start = None
                row.interval_3_end = None

        await session.commit()

    await callback.answer("Готово")
    await callback.message.answer(
        "✅ Готово. Применены базовые настройки:\n"
        "• Пн–Пт рабочие, Сб–Вс выходные\n"
        "• Интервалы: 09:00–12:00, 13:00–17:00, 17:00–21:00\n"
        "• Длительность: 60 мин, буфер: 10 мин\n"
        "• Шаг начала слотов: 15 мин\n"
        "• Максимум сессий в день: 4\n"
        "Правило записи: бронирование и изменение доступны только на следующий день и только до 21:00 предыдущего дня по вашему времени.\n\n"
        "Теперь можно проверять /status и переходить к расширенным настройкам (в разработке)."
    )


@router.callback_query(F.data == "owner_panel:slot_step_menu")
async def owner_panel_slot_step_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "Выберите шаг начала слотов (в минутах):",
        reply_markup=_slot_step_keyboard(),
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

    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile is None:
            if owner_tg_user_id is None:
                await callback.answer("Профиль не найден", show_alert=True)
                return
            profile = SpecialistProfile(
                specialist_id=specialist_id,
                public_name=public_name or "Специалист",
                owner_tg_user_id=owner_tg_user_id,
                owner_tg_username=None,
                specialist_timezone="UTC",
                session_duration_min=_DEFAULT_DURATION_MIN,
                session_buffer_min=_DEFAULT_BUFFER_MIN,
                max_sessions_per_day=_DEFAULT_MAX_SESSIONS_PER_DAY,
                slot_step_min=_DEFAULT_SLOT_STEP_MIN,
                cancel_window_hours=_DEFAULT_CANCEL_WINDOW_HOURS,
            )
            session.add(profile)

        profile.slot_step_min = step_min
        await session.commit()

    await callback.answer()
    await callback.message.answer(f"Шаг начала слотов обновлён: {step_min} мин")
    await send_owner_panel(callback.message, specialist_id=specialist_id, public_name=public_name)


@router.callback_query(F.data == "owner_panel:manual")
async def owner_panel_manual(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🛠 Ручная настройка скоро появится. Пока можно применить дефолтные параметры кнопкой выше."
    )


@router.callback_query(F.data == "owner_panel:skip")
async def owner_panel_skip(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "⏭ Пропущено. Вы можете вернуться к настройкам позже через deep-link owner_panel."
    )
