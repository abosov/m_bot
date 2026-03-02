from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import PUBLIC_SITE_URL
from database import Appointment, BookingState, SpecialistProfile, TariffPlan

_UPSELL_TEXT = (
    "Вы используете Zumbot активно 👍\n"
    "Хотите видеть полную статистику по записям и отменам?\n"
    "Аналитика доступна на тарифе Pro."
)
_UPSELL_BUTTON_TEXT = "Посмотреть тариф Pro"


def _month_start(value: datetime) -> datetime:
    current = value.astimezone(timezone.utc)
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _target_threshold(plan: TariffPlan | str | None) -> int | None:
    plan_value = plan.value if isinstance(plan, TariffPlan) else str(plan)
    if plan_value == TariffPlan.free.value:
        return 12  # ceil(16 * 0.7)
    if plan_value == TariffPlan.start.value:
        return 70  # ceil(100 * 0.7)
    return None


async def maybe_mark_analytics_upsell_needed(
    *,
    session: AsyncSession,
    profile: SpecialistProfile | None,
    specialist_id,
    now_utc: datetime | None = None,
) -> bool:
    if profile is None or not hasattr(session, "scalar"):
        return False

    threshold = _target_threshold(getattr(profile, "tariff_plan", None))
    if threshold is None:
        return False

    now_value = now_utc or datetime.now(timezone.utc)
    current_month_start = _month_start(now_value)

    prompted_at = getattr(profile, "analytics_upsell_prompted_at", None)
    if prompted_at is not None and _month_start(prompted_at) >= current_month_start:
        return False

    monthly_count = await session.scalar(
        select(func.count())
        .select_from(Appointment)
        .where(Appointment.specialist_id == specialist_id)
        .where(Appointment.start_at_utc >= current_month_start)
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

    if int(monthly_count or 0) < threshold:
        return False

    profile.analytics_upsell_prompted_at = now_value
    return True


def upsell_message_text() -> str:
    return _UPSELL_TEXT


def upsell_pricing_url() -> str:
    return f"{PUBLIC_SITE_URL}/pricing"


def upsell_button_text() -> str:
    return _UPSELL_BUTTON_TEXT
