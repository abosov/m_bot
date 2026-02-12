import logging
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import (
    Specialist,
    SpecialistProfile,
    SpecialistAuthTelegram,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    async_session_factory,
)
from services.google_calendar import list_calendars, create_bot_calendar, create_and_cleanup_test_event
from services.specialist_defaults import apply_specialist_defaults_if_missing
from services.notify import notify_exception
from handlers.personal_bot.routers.common.start import _render_onboarding_screen

router = Router(name="personal_bot_common_calendar")
logger = logging.getLogger(__name__)


class PersonalGoogleCalendarPickState(StatesGroup):
    items = State()
    page = State()


def _calendar_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Создать новый", callback_data="calendar:create")],
            [InlineKeyboardButton(text="📂 Выбрать существующий", callback_data="calendar:select")],
            [InlineKeyboardButton(text="Отмена", callback_data="calendar:cancel_select")],
        ]
    )


def _calendar_select_text(*, total: int, page: int, page_size: int) -> str:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return (
        "📂 Выберите рабочий Google Календарь.\n"
        f"Найдено календарей: {total}. Страница {page + 1}/{total_pages}.\n"
        "После выбора будет запущен smoke-test (создание и удаление тестового события)."
    )


def _calendar_select_keyboard(*, items: list[dict], page: int, page_size: int) -> InlineKeyboardMarkup:
    total = len(items)
    rows: list[list[InlineKeyboardButton]] = []
    if total:
        max_page = max(0, (total - 1) // page_size)
        page = max(0, min(page, max_page))
        start = page * page_size
        end = min(start + page_size, total)

        for idx in range(start, end):
            item = items[idx]
            summary = item.get("summary") or "Без названия"
            if item.get("readOnly"):
                summary = f"{summary} (только чтение)"
            rows.append([
                InlineKeyboardButton(text=summary, callback_data=f"calendar:pick:{idx}")
            ])

        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"calendar:page:{page - 1}"))
        if end < total:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"calendar:page:{page + 1}"))
        if nav:
            rows.append(nav)

    rows.append([InlineKeyboardButton(text="Отмена", callback_data="calendar:cancel_select")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _upsert_calendar_settings(*, specialist_id: int, calendar_id: str, calendar_summary: str | None, smoke_status: str | None) -> None:
    async with async_session_factory() as session:
        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        now = datetime.now(timezone.utc)
        if settings is None:
            settings = SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                calendar_summary=calendar_summary,
                source=SpecialistCalendarSource.selected,
            )
            session.add(settings)
        else:
            settings.calendar_id = calendar_id
            settings.calendar_summary = calendar_summary

        settings.last_smoke_test_status = smoke_status
        settings.last_smoke_test_at = now
        settings.last_smoke_test_error = None
        await session.commit()


async def _get_specialist_id_by_tg_user_id(tg_user_id: int):
    async with async_session_factory() as session:
        auth = (
            await session.execute(
                select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
            )
        ).scalar_one_or_none()
    return auth.specialist_id if auth else None


@router.callback_query(F.data == "calendar:switch_stub")
async def personal_calendar_switch_stub(callback: types.CallbackQuery, state: FSMContext):
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    await callback.message.answer(
        "Шаг: выберите действие с календарём (создать отдельный или выбрать существующий).",
        reply_markup=_calendar_action_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "calendar:create")
async def personal_calendar_create(callback: types.CallbackQuery, state: FSMContext):
    tg_user_id = callback.from_user.id
    specialist_id = await _get_specialist_id_by_tg_user_id(tg_user_id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    try:
        async with async_session_factory() as session:
            specialist = (
                await session.execute(
                    select(Specialist)
                    .options(selectinload(Specialist.profile), selectinload(Specialist.calendar_settings))
                    .where(Specialist.specialist_id == specialist_id)
                )
            ).scalar_one_or_none()

        if specialist is None:
            await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
            await callback.answer()
            return

        profile = specialist.profile
        if profile is None:
            await callback.message.answer("⚠️ Сначала заполните профиль через /start.")
            await callback.answer()
            return

        calendar_name = (profile.public_name or "Специалист").strip() or "Специалист"
        calendar = await create_bot_calendar(specialist_id, calendar_name, profile.specialist_timezone or "UTC")
        calendar_id = calendar.get("id")
        summary = calendar.get("summary")
        calendar_tz = calendar.get("timeZone") or profile.specialist_timezone or "UTC"

        smoke_status = "ok"
        try:
            await create_and_cleanup_test_event(specialist_id, calendar_id, calendar_tz)
        except Exception:
            smoke_status = "failed"

        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=calendar_id,
            calendar_summary=summary,
            smoke_status=smoke_status,
        )

        async with async_session_factory() as session:
            await apply_specialist_defaults_if_missing(session, specialist_id)
            await session.commit()

        await callback.message.answer("✅ Календарь подключён.")
        await _render_onboarding_screen(callback.message, specialist_id)
    except Exception as exc:
        await notify_exception(
            where="handlers.personal_bot.common.calendar.personal_calendar_create",
            exc=exc,
            context={"tg_user_id": tg_user_id},
            event=callback,
        )
        await callback.message.answer("⚠️ Не удалось подключить календарь. Попробуйте позже.")

    await callback.answer()


@router.callback_query(F.data == "calendar:select")
async def personal_calendar_select(callback: types.CallbackQuery, state: FSMContext):
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    items_raw = await list_calendars(specialist_id)
    items: list[dict] = []
    for item in items_raw:
        item_id = item.get("id")
        if not item_id:
            continue
        access_role = item.get("accessRole")
        items.append(
            {
                "id": item_id,
                "summary": item.get("summary"),
                "accessRole": access_role,
                "readOnly": access_role == "reader",
                "timeZone": item.get("timeZone"),
            }
        )

    await state.update_data(items=items, page=0)
    await state.set_state(PersonalGoogleCalendarPickState.items)

    await callback.message.answer(
        _calendar_select_text(total=len(items), page=0, page_size=5),
        reply_markup=_calendar_select_keyboard(items=items, page=0, page_size=5),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar:page:"))
async def personal_calendar_page(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    items = data.get("items") or []
    try:
        page = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректная страница")
        return

    max_page = max(0, (len(items) - 1) // 5) if items else 0
    page = max(0, min(page, max_page))
    await state.update_data(page=page)

    await callback.message.edit_text(
        _calendar_select_text(total=len(items), page=page, page_size=5),
        reply_markup=_calendar_select_keyboard(items=items, page=page, page_size=5),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar:pick:"))
async def personal_calendar_pick(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    items = data.get("items") or []

    try:
        idx = int((callback.data or "").split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный выбор")
        return

    if idx < 0 or idx >= len(items):
        await callback.message.answer("⚠️ Выбранный календарь не найден. Откройте список заново через /start.")
        await callback.answer()
        return

    item = items[idx]
    if item.get("readOnly"):
        await callback.answer("Этот календарь только для чтения — выберите другой.", show_alert=True)
        return

    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    calendar_tz = item.get("timeZone") or "UTC"
    smoke_status = "ok"
    try:
        await create_and_cleanup_test_event(specialist_id, item["id"], calendar_tz)
    except Exception:
        smoke_status = "failed"

    await _upsert_calendar_settings(
        specialist_id=specialist_id,
        calendar_id=item["id"],
        calendar_summary=item.get("summary"),
        smoke_status=smoke_status,
    )

    async with async_session_factory() as session:
        await apply_specialist_defaults_if_missing(session, specialist_id)
        await session.commit()

    await state.clear()
    await callback.message.answer("✅ Календарь применён.")
    await _render_onboarding_screen(callback.message, specialist_id)
    await callback.answer()


@router.callback_query(F.data == "calendar:cancel_select")
async def personal_calendar_cancel_select(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if specialist_id:
        await _render_onboarding_screen(callback.message, specialist_id)
    else:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
    await callback.answer()


@router.callback_query(F.data == "calendar:smoke")
async def personal_calendar_smoke(callback: types.CallbackQuery, state: FSMContext):
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    async with async_session_factory() as session:
        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        profile = await session.get(SpecialistProfile, specialist_id)

    if settings is None or not settings.calendar_id:
        await callback.message.answer("⚠️ Календарь ещё не подключен.")
        await callback.answer()
        return

    tz = settings.calendar_time_zone or (profile.specialist_timezone if profile else None) or "UTC"
    try:
        await create_and_cleanup_test_event(specialist_id, settings.calendar_id, tz)
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            calendar_summary=settings.calendar_summary,
            smoke_status="ok",
        )
        await callback.message.answer("✅ Smoke-test выполнен успешно.")
    except Exception as exc:
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            calendar_summary=settings.calendar_summary,
            smoke_status="failed",
        )
        await notify_exception(
            where="handlers.personal_bot.common.calendar.personal_calendar_smoke",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
        )
        await callback.message.answer("⚠️ Smoke-test не пройден.")

    await callback.answer()
