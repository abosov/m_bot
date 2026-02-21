from __future__ import annotations

import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from database import Appointment, BookingState, async_session_factory
from services.specialist_appointments import confirm_appointment_by_specialist, reject_appointment_by_specialist

router = Router(name="personal_bot_specialist_appointment_confirmations")
logger = logging.getLogger(__name__)

_STALE_TEXT = "Эта заявка уже обработана или устарела."
_REJECT_MODE_PARSE_ERROR_TEXT = "Не удалось обработать действие, попробуйте ещё раз"
_REJECTION_REASON_LIMIT = 1000
_REJECT_MODE_CALLBACK_PREFIX = "sp_appt_rej_mode"
_REJECT_MODE_WITH_REASON_TOKEN = "wr"
_REJECT_MODE_NO_REASON_TOKEN = "nr"


async def _safe_clear_inline_keyboard(message: Message) -> None:
    try:
        await message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest as exc:
        # Сообщение могло быть уже отредактировано/удалено другим обработчиком.
        logger.info("Unable to clear inline keyboard: %s", exc)


def _format_appointment_slot(appointment: Appointment) -> str:
    return appointment.start_at_utc.strftime("%d.%m %H:%M")


class SpecialistAppointmentRejectStates(StatesGroup):
    waiting_rejection_reason = State()


def _reject_with_or_without_reason_keyboard(appointment_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оставить пояснение",
                    callback_data=f"{_REJECT_MODE_CALLBACK_PREFIX}:{_REJECT_MODE_WITH_REASON_TOKEN}:{appointment_id}",
                ),
                InlineKeyboardButton(
                    text="Без пояснений",
                    callback_data=f"{_REJECT_MODE_CALLBACK_PREFIX}:{_REJECT_MODE_NO_REASON_TOKEN}:{appointment_id}",
                ),
            ]
        ]
    )


def _reject_no_reason_inline_keyboard(appointment_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Без пояснений",
                    callback_data=f"{_REJECT_MODE_CALLBACK_PREFIX}:{_REJECT_MODE_NO_REASON_TOKEN}:{appointment_id}",
                )
            ]
        ]
    )


def _parse_reject_mode_callback_data(callback_data: str | None) -> tuple[str, UUID]:
    parts = (callback_data or "").split(":")
    if len(parts) != 3:
        raise ValueError("invalid callback_data parts count")

    prefix, mode_token, appointment_raw = parts
    if prefix not in {_REJECT_MODE_CALLBACK_PREFIX, "sp_appt_reject_mode"}:
        raise ValueError("invalid callback_data prefix")

    mode_map = {
        _REJECT_MODE_WITH_REASON_TOKEN: "with_reason",
        _REJECT_MODE_NO_REASON_TOKEN: "no_reason",
        "with_reason": "with_reason",
        "no_reason": "no_reason",
    }
    mode = mode_map.get(mode_token)
    if mode is None:
        raise ValueError("invalid reject mode token")

    try:
        appointment_id = UUID(appointment_raw)
    except ValueError as exc:
        raise ValueError("invalid appointment_id") from exc

    return mode, appointment_id


async def _resolve_pending_appointment(appointment_id: UUID, specialist_id) -> Appointment | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .where(Appointment.specialist_id == specialist_id)
        )
        appointment = result.scalar_one_or_none()

    if appointment is None or appointment.booking_state != BookingState.awaiting_specialist_confirmation:
        return None
    return appointment


@router.callback_query(F.data.startswith("sp_appt_decision:"))
async def specialist_appointment_decision(callback: CallbackQuery, specialist_id) -> None:
    if callback.message is None:
        await callback.answer()
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные кнопки.", show_alert=True)
        return

    _, action, appointment_raw = parts
    if action not in {"confirm", "reject"}:
        await callback.answer("Некорректное действие.", show_alert=True)
        return

    try:
        appointment_id = UUID(appointment_raw)
    except ValueError:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if action == "confirm":
        async with async_session_factory() as session:
            result = await confirm_appointment_by_specialist(
                session,
                appointment_id=appointment_id,
                specialist_id=specialist_id,
            )

        if result.status in {"ok", "updated"}:
            await _safe_clear_inline_keyboard(callback.message)
            await callback.answer("✅ Запись подтверждена")
            return

        await callback.answer(_STALE_TEXT, show_alert=True)
        return

    appointment = await _resolve_pending_appointment(appointment_id, specialist_id)
    if appointment is None:
        await callback.answer(_STALE_TEXT, show_alert=True)
        return

    await _safe_clear_inline_keyboard(callback.message)
    await callback.message.answer(
        "Добавить пояснение клиенту?",
        reply_markup=_reject_with_or_without_reason_keyboard(appointment_id),
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith(f"{_REJECT_MODE_CALLBACK_PREFIX}:")
    | F.data.startswith("sp_appt_reject_mode:")
)
async def specialist_appointment_reject_mode(callback: CallbackQuery, specialist_id, state: FSMContext) -> None:
    await callback.answer()

    if callback.message is None:
        return

    try:
        mode, appointment_id = _parse_reject_mode_callback_data(callback.data)
    except ValueError:
        logger.exception("Invalid reject mode callback_data: %s", callback.data)
        await callback.message.answer(_REJECT_MODE_PARSE_ERROR_TEXT)
        return

    appointment = await _resolve_pending_appointment(appointment_id, specialist_id)
    if appointment is None:
        await state.clear()
        await callback.answer(_STALE_TEXT, show_alert=True)
        return

    if mode == "no_reason":
        async with async_session_factory() as session:
            result = await reject_appointment_by_specialist(
                session,
                appointment_id=appointment_id,
                specialist_id=specialist_id,
                rejection_reason=None,
            )
        await state.clear()

        if result.status == "updated":
            await _safe_clear_inline_keyboard(callback.message)
            await callback.message.answer(f"Запись отклонена: {_format_appointment_slot(appointment)}")
            return

        await callback.message.answer(_STALE_TEXT)
        return

    await state.set_state(SpecialistAppointmentRejectStates.waiting_rejection_reason)
    await state.update_data(appointment_id=str(appointment_id), request_message_id=callback.message.message_id)
    await _safe_clear_inline_keyboard(callback.message)
    await callback.message.answer("Введите пояснение одним сообщением.")


@router.message(SpecialistAppointmentRejectStates.waiting_rejection_reason)
async def specialist_appointment_reject_reason_input(message: Message, specialist_id, state: FSMContext) -> None:
    data = await state.get_data()
    appointment_raw = data.get("appointment_id")
    if not appointment_raw:
        await state.clear()
        await message.answer("Эта заявка уже обработана или устарела.")
        return

    try:
        appointment_id = UUID(str(appointment_raw))
    except ValueError:
        await state.clear()
        await message.answer("Эта заявка уже обработана или устарела.")
        return

    text = (message.text or "").strip()
    if not text:
        await message.answer(
            "Пояснение не должно быть пустым. Введите текст или выберите вариант без пояснений:",
            reply_markup=_reject_no_reason_inline_keyboard(appointment_id),
        )
        return

    if len(text) > _REJECTION_REASON_LIMIT:
        await message.answer(f"Пояснение слишком длинное. Сократите до {_REJECTION_REASON_LIMIT} символов.")
        return

    appointment = await _resolve_pending_appointment(appointment_id, specialist_id)
    if appointment is None:
        await state.clear()
        await message.answer("Эта заявка уже обработана или устарела.")
        return

    async with async_session_factory() as session:
        result = await reject_appointment_by_specialist(
            session,
            appointment_id=appointment_id,
            specialist_id=specialist_id,
            rejection_reason=text,
        )

    await state.clear()
    if result.status == "updated":
        await message.answer("Запись отклонена, пояснение отправлено клиенту")
        return

    await message.answer("Эта заявка уже обработана или устарела.")
