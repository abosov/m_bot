from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from database import Appointment, BookingState, async_session_factory
from services.specialist_appointments import confirm_appointment_by_specialist

router = Router(name="personal_bot_specialist_appointment_confirmations")

_STALE_TEXT = "Эта заявка уже обработана или устарела."


def _reject_reason_keyboard(appointment_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Неподходящее время", callback_data=f"sp_appt_reject_reason:{appointment_id}:time")],
            [InlineKeyboardButton(text="Лимит на день", callback_data=f"sp_appt_reject_reason:{appointment_id}:limit")],
            [InlineKeyboardButton(text="Другая причина", callback_data=f"sp_appt_reject_reason:{appointment_id}:other")],
        ]
    )


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

        if result.status == "updated":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("✅ Запись подтверждена")
            return

        await callback.answer(_STALE_TEXT, show_alert=True)
        return

    async with async_session_factory() as session:
        appointment = await session.execute(
            select(Appointment)
            .where(Appointment.appointment_id == appointment_id)
            .where(Appointment.specialist_id == specialist_id)
        )
        appointment = appointment.scalar_one_or_none()

    if appointment is None or appointment.booking_state in (BookingState.confirmed, BookingState.rejected_by_specialist):
        await callback.answer(_STALE_TEXT, show_alert=True)
        return

    await callback.message.answer(
        "Выберите причину отклонения:",
        reply_markup=_reject_reason_keyboard(appointment_id),
    )
    await callback.answer()
