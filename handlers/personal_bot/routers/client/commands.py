from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database import Client, SpecialistProfile, async_session_factory
from services.booking_policy import validate_next_day_cutoff

router = Router(name="personal_bot_client_commands")


class ClientBookingState(StatesGroup):
    waiting_for_day = State()


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
async def client_pick_day(callback, state: FSMContext) -> None:
    selected_iso = callback.data.removeprefix("client_book_day:")
    await state.update_data(booking_date=selected_iso)

    selected_day = date.fromisoformat(selected_iso)
    await callback.message.answer(
        f"Вы выбрали {selected_day.strftime('%d.%m.%Y')}. Далее будет выбор времени (в разработке)."
    )
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
