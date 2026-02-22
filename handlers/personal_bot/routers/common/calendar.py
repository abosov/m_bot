import logging
from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import (
    SpecialistAuthTelegram,
    SpecialistCalendarSettings,
    SpecialistCalendarSource,
    async_session_factory,
)
from services.google_calendar import (
    list_calendars,
    create_and_cleanup_test_event,
)
from handlers.personal_bot.routers.common.start import _render_onboarding_screen
from services.log_context import log_event
from services.telegram.calendar_keyboard import build_calendar_selection_keyboard

router = Router(name="personal_bot_common_calendar")
logger = logging.getLogger(__name__)


def _log_personal_handler(*, callback: types.CallbackQuery, handler_name: str, fsm_state: str | None, outcome: str) -> None:
    log_event(
        logger,
        logging.INFO,
        event="personal_handler",
        bot_id=callback.bot.id,
        tg_user_id=callback.from_user.id if callback.from_user else None,
        handler_name=handler_name,
        fsm_state=fsm_state,
        outcome=outcome,
        update_type="callback_query",
        text_length=None,
    )


class PersonalGoogleCalendarPickState(StatesGroup):
    items = State()
    page = State()


def _calendar_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 Выбрать календарь", callback_data="calendar:select")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="calendar:cancel_select")],
        ]
    )


def _calendar_select_text(*, total: int, page: int, page_size: int) -> str:
    _ = (page, page_size)
    return (
        "📂 Выберите рабочий Google Календарь\n\n"
        f"Найдено календарей: {total}.\n"
        "После выбора будет выполнена проверка интеграции."
    )


def _calendar_select_keyboard(*, items: list[dict], page: int, page_size: int) -> InlineKeyboardMarkup:
    return build_calendar_selection_keyboard(items, page=page, per_page=page_size)


async def _upsert_calendar_settings(
    *,
    specialist_id: int,
    calendar_id: str,
    calendar_summary: str | None,
    calendar_tz: str | None,
    smoke_status: str | None,
) -> None:
    async with async_session_factory() as session:
        settings = await session.get(SpecialistCalendarSettings, specialist_id)
        now = datetime.now(timezone.utc)
        if settings is None:
            settings = SpecialistCalendarSettings(
                specialist_id=specialist_id,
                calendar_id=calendar_id,
                calendar_summary=calendar_summary,
                source=SpecialistCalendarSource.selected,
                calendar_time_zone=calendar_tz,
            )
            session.add(settings)
        else:
            settings.calendar_id = calendar_id
            settings.calendar_summary = calendar_summary
            settings.calendar_time_zone = calendar_tz

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
    _log_personal_handler(callback=callback, handler_name="personal_calendar_switch_stub", fsm_state=await state.get_state(), outcome="start")
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if not specialist_id:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
        await callback.answer()
        return

    await callback.message.answer(
        "Шаг: выберите рабочий Google Календарь.",
        reply_markup=_calendar_action_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "calendar:create")
async def personal_calendar_create_legacy_redirect(callback: types.CallbackQuery, state: FSMContext):
    _log_personal_handler(
        callback=callback,
        handler_name="personal_calendar_create_legacy_redirect",
        fsm_state=await state.get_state(),
        outcome="legacy_redirect_to_select",
    )
    callback.data = "calendar:select"
    await personal_calendar_select(callback, state)


@router.callback_query(F.data == "calendar:select")
async def personal_calendar_select(callback: types.CallbackQuery, state: FSMContext):
    _log_personal_handler(callback=callback, handler_name="personal_calendar_select", fsm_state=await state.get_state(), outcome="start")
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
                "primary": bool(item.get("primary")),
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


@router.callback_query(F.data == "calendar:refresh")
async def personal_calendar_refresh(callback: types.CallbackQuery, state: FSMContext):
    await personal_calendar_select(callback, state)


@router.callback_query(F.data.startswith("calendar:page:"))
async def personal_calendar_page(callback: types.CallbackQuery, state: FSMContext):
    _log_personal_handler(callback=callback, handler_name="personal_calendar_page", fsm_state=await state.get_state(), outcome="start")
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
    _log_personal_handler(callback=callback, handler_name="personal_calendar_pick", fsm_state=await state.get_state(), outcome="start")
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
        calendar_tz=calendar_tz,
        smoke_status=smoke_status,
    )

    async with async_session_factory() as session:
        await apply_specialist_defaults_if_missing(session, specialist_id, preferred_timezone=calendar_tz)
        await session.commit()

    await state.clear()
    await callback.message.answer("✅ Календарь применён.")
    await _render_onboarding_screen(callback.message, specialist_id)
    await callback.answer()


@router.callback_query(F.data == "calendar:cancel_select")
async def personal_calendar_cancel_select(callback: types.CallbackQuery, state: FSMContext):
    _log_personal_handler(callback=callback, handler_name="personal_calendar_cancel_select", fsm_state=await state.get_state(), outcome="start")
    await state.clear()
    specialist_id = await _get_specialist_id_by_tg_user_id(callback.from_user.id)
    if specialist_id:
        await _render_onboarding_screen(callback.message, specialist_id)
    else:
        await callback.message.answer("⚠️ Профиль специалиста не найден. Нажмите /start.")
    await callback.answer()


@router.callback_query(F.data == "calendar:smoke")
async def personal_calendar_smoke(callback: types.CallbackQuery, state: FSMContext):
    _log_personal_handler(callback=callback, handler_name="personal_calendar_smoke", fsm_state=await state.get_state(), outcome="start")
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
            calendar_tz=tz,
            smoke_status="ok",
        )
        await callback.message.answer("✅ Интеграция выполнена успешно.")
    except Exception as exc:
        await _upsert_calendar_settings(
            specialist_id=specialist_id,
            calendar_id=settings.calendar_id,
            calendar_summary=settings.calendar_summary,
            calendar_tz=tz,
            smoke_status="failed",
        )
        await notify_exception(
            where="handlers.personal_bot.common.calendar.personal_calendar_smoke",
            exc=exc,
            context={"tg_user_id": callback.from_user.id},
            event=callback,
        )
        await callback.message.answer("⚠️ Интеграция не завершена.")

    await callback.answer()
