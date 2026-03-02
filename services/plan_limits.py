from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Appointment, BookingState, SpecialistProfile, TariffPlan

FREE_PLAN_MONTHLY_LIMIT = 16
FREE_PLAN_LIMIT_REACHED_ERROR = (
    "Вы достигли лимита бесплатного тарифа (16 записей в месяц). "
    "Обновите тариф для продолжения."
)


class PlanLimitError(ValueError):
    pass


def _month_range_utc(at_utc: datetime) -> tuple[datetime, datetime]:
    current = at_utc.astimezone(timezone.utc)
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return month_start, month_end


async def enforce_booking_plan_limit(
    *,
    session: AsyncSession,
    profile: SpecialistProfile | None,
    specialist_id,
    slot_start_utc: datetime,
) -> None:
    tariff_plan = getattr(profile, "tariff_plan", TariffPlan.start)
    if tariff_plan != TariffPlan.free:
        return

    month_start, month_end = _month_range_utc(slot_start_utc)

    monthly_count = await session.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.specialist_id == specialist_id)
        .where(Appointment.start_at_utc >= month_start)
        .where(Appointment.start_at_utc < month_end)
        .where(
            Appointment.booking_state.in_(
                (
                    BookingState.pending,
                    BookingState.awaiting_specialist_confirmation,
                    BookingState.confirmed,
                )
            )
        )
    )

    if int(monthly_count or 0) >= FREE_PLAN_MONTHLY_LIMIT:
        raise PlanLimitError(FREE_PLAN_LIMIT_REACHED_ERROR)
