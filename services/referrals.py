from __future__ import annotations

import calendar
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import PUBLIC_SITE_URL
from database import GoogleOAuth, GoogleOAuthStatus, Specialist, SpecialistProfile, TariffPlan


def build_referral_link(referral_code: str) -> str:
    return f"{PUBLIC_SITE_URL}/?ref={referral_code}"


def extract_referral_code(start_args: str | None) -> str | None:
    if not start_args:
        return None
    raw = start_args.strip()
    if not raw:
        return None
    if raw.lower().startswith("ref_"):
        raw = raw[4:]
    normalized = "".join(ch for ch in raw.upper() if ch.isalnum())
    return normalized[:16] or None


def _add_months(base: datetime, months: int) -> datetime:
    source = base.astimezone(timezone.utc)
    year = source.year + (source.month - 1 + months) // 12
    month = (source.month - 1 + months) % 12 + 1
    day = min(source.day, calendar.monthrange(year, month)[1])
    return source.replace(year=year, month=month, day=day)


async def count_active_referrals(session: AsyncSession, specialist_id: UUID) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Specialist)
        .where(Specialist.referrer_id == specialist_id)
        .where(Specialist.referral_bonus_awarded_at.is_not(None))
    )
    return int(value or 0)


async def attach_referrer_by_code(session: AsyncSession, specialist: Specialist, referral_code: str | None) -> None:
    if not referral_code:
        return
    referrer = (
        await session.execute(
            select(Specialist).where(Specialist.referral_code == referral_code).limit(1)
        )
    ).scalar_one_or_none()
    if referrer is None:
        return
    if referrer.specialist_id == specialist.specialist_id:
        return
    specialist.referrer_id = referrer.specialist_id


async def process_referral_activation(session: AsyncSession, referred_specialist_id: UUID) -> bool:
    referred = await session.get(Specialist, referred_specialist_id)
    if referred is None or referred.referrer_id is None or referred.referral_bonus_awarded_at is not None:
        return False

    oauth_connected = await session.scalar(
        select(func.count())
        .select_from(GoogleOAuth)
        .where(GoogleOAuth.specialist_id == referred_specialist_id)
        .where(GoogleOAuth.status == GoogleOAuthStatus.connected)
    )
    if int(oauth_connected or 0) == 0:
        return False

    referrer = await session.get(Specialist, referred.referrer_id)
    if referrer is None:
        return False

    referrer_profile = await session.get(SpecialistProfile, referrer.specialist_id)
    if referrer_profile is None:
        return False

    now_utc = datetime.now(timezone.utc)
    referrer_profile.referral_bonus_months = int(referrer_profile.referral_bonus_months or 0) + 1

    if referrer_profile.tariff_plan in (TariffPlan.free, TariffPlan.start):
        current_bonus_until = referrer_profile.start_bonus_until
        base = current_bonus_until if current_bonus_until and current_bonus_until > now_utc else now_utc
        referrer_profile.start_bonus_until = _add_months(base, 1)
        if referrer_profile.tariff_plan == TariffPlan.free:
            referrer_profile.tariff_plan = TariffPlan.start

    referred.referral_bonus_awarded_at = now_utc
    return True
