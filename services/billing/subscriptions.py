import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import config
from sqlalchemy import select
from database import (
    BillingPeriod,
    BillingPurchase,
    BillingPurchaseStatus,
    SpecialistAuthTelegram,
    SpecialistProfile,
    TariffPlan,
    async_session_factory,
    get_billing_purchase_by_token_hash,
    get_billing_purchase_by_yookassa_payment_id,
    get_latest_billing_purchase_for_tg_user,
    set_billing_purchase_status,
    set_billing_purchase_yookassa_fields,
)
from services.integrations.yookassa_client import YooKassaClient

_PURCHASE_TTL_MINUTES = 30

_PERIOD_LABELS = {
    BillingPeriod.monthly: "месяц",
    BillingPeriod.yearly: "год",
}

_PLAN_PERIOD_AMOUNT_RUB = {
    (TariffPlan.free, BillingPeriod.monthly): 0,
    (TariffPlan.free, BillingPeriod.yearly): 0,
    (TariffPlan.start, BillingPeriod.monthly): 990,
    (TariffPlan.start, BillingPeriod.yearly): 790,
    (TariffPlan.pro, BillingPeriod.monthly): 2490,
    (TariffPlan.pro, BillingPeriod.yearly): 1990,
    (TariffPlan.team, BillingPeriod.monthly): 4990,
    (TariffPlan.team, BillingPeriod.yearly): 3990,
}


class BillingError(Exception):
    pass


def _normalize_plan(plan: TariffPlan | str) -> TariffPlan:
    if isinstance(plan, TariffPlan):
        return plan
    return TariffPlan(str(plan).strip().lower())


def _normalize_period(period: BillingPeriod | str) -> BillingPeriod:
    if isinstance(period, BillingPeriod):
        return period
    raw = str(period).strip().lower()
    if raw == "m":
        return BillingPeriod.monthly
    if raw == "y":
        return BillingPeriod.yearly
    return BillingPeriod(raw)


def _pay_token_pepper() -> str:
    return config.WEB_CONNECT_PEPPER or config.ENCRYPTION_KEY or "zumbot-billing-pepper"


def hash_pay_token(raw_token: str) -> str:
    payload = f"{raw_token}{_pay_token_pepper()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def create_subscription_purchase(
    specialist_id: uuid.UUID,
    tg_user_id: int,
    plan: TariffPlan | str,
    period: BillingPeriod | str,
) -> tuple[str, str]:
    normalized_plan = _normalize_plan(plan)
    normalized_period = _normalize_period(period)
    amount_rub_int = _PLAN_PERIOD_AMOUNT_RUB[(normalized_plan, normalized_period)]

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=_PURCHASE_TTL_MINUTES)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_pay_token(raw_token)

    purchase = BillingPurchase(
        purchase_id=uuid.uuid4(),
        specialist_id=specialist_id,
        tg_user_id=tg_user_id,
        plan=normalized_plan,
        period=normalized_period,
        amount_rub_int=amount_rub_int,
        currency="RUB",
        status=BillingPurchaseStatus.pending,
        pay_token_hash=token_hash,
        expires_at=expires_at,
        used_at=None,
        yookassa_payment_id=None,
        yookassa_status=None,
        created_at=now,
        updated_at=now,
    )

    async with async_session_factory() as session:
        session.add(purchase)
        await session.commit()

    pay_url = f"{config.PUBLIC_SITE_URL}/pay?token={raw_token}"
    return raw_token, pay_url


async def get_purchase_for_raw_token(raw_token: str) -> BillingPurchase | None:
    token_hash = hash_pay_token(raw_token)
    async with async_session_factory() as session:
        return await get_billing_purchase_by_token_hash(session, token_hash)


async def create_yookassa_payment_for_token(raw_token: str) -> str:
    purchase = await get_purchase_for_raw_token(raw_token)
    if purchase is None:
        raise BillingError("invalid_token")

    now = datetime.now(timezone.utc)
    if purchase.expires_at <= now:
        raise BillingError("token_expired")
    if purchase.used_at is not None:
        raise BillingError("token_used")

    client = YooKassaClient()
    result = await client.create_payment(
        amount_rub_int=purchase.amount_rub_int,
        description=f"Zumbot {purchase.plan.value}/{purchase.period.value}",
        return_url=f"{config.PUBLIC_SITE_URL}/pay?token={raw_token}",
    )

    payment_id = str(result.get("id"))
    payment_status = str(result.get("status") or "pending")
    confirmation = result.get("confirmation") if isinstance(result.get("confirmation"), dict) else {}
    confirmation_url = str(confirmation.get("confirmation_url") or "")

    async with async_session_factory() as session:
        await set_billing_purchase_yookassa_fields(
            session,
            purchase.purchase_id,
            yookassa_payment_id=payment_id,
            yookassa_status=payment_status,
        )
        await set_billing_purchase_status(session, purchase.purchase_id, BillingPurchaseStatus.awaiting_payment)
        await session.commit()

    if not confirmation_url:
        raise BillingError("missing_confirmation_url")
    return confirmation_url


async def process_yookassa_webhook(event_payload: dict) -> str:
    obj = event_payload.get("object") if isinstance(event_payload, dict) else None
    if not isinstance(obj, dict):
        raise BillingError("invalid_payload")

    payment_id = str(obj.get("id") or "")
    payment_status = str(obj.get("status") or "")
    if not payment_id:
        raise BillingError("missing_payment_id")

    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        purchase = await get_billing_purchase_by_yookassa_payment_id(session, payment_id)
        if purchase is None:
            raise BillingError("purchase_not_found")

        # idempotent updates
        await set_billing_purchase_yookassa_fields(
            session,
            purchase.purchase_id,
            yookassa_payment_id=payment_id,
            yookassa_status=payment_status,
        )

        if payment_status == "succeeded":
            if purchase.status != BillingPurchaseStatus.succeeded:
                await set_billing_purchase_status(session, purchase.purchase_id, BillingPurchaseStatus.succeeded)
                purchase.used_at = purchase.used_at or now
                profile = await session.get(SpecialistProfile, purchase.specialist_id)
                if profile is not None:
                    period_delta = timedelta(days=30) if purchase.period == BillingPeriod.monthly else timedelta(days=365)
                    profile.tariff_plan = purchase.plan
                    profile.tariff_period = purchase.period
                    profile.tariff_last_paid_at = now
                    profile.tariff_paid_until = now + period_delta
        elif payment_status == "canceled":
            await set_billing_purchase_status(session, purchase.purchase_id, BillingPurchaseStatus.canceled)
        elif payment_status in {"waiting_for_capture", "pending"}:
            await set_billing_purchase_status(session, purchase.purchase_id, BillingPurchaseStatus.awaiting_payment)
        else:
            await set_billing_purchase_status(session, purchase.purchase_id, BillingPurchaseStatus.error)

        await session.commit()
    return payment_status


async def get_latest_purchase_status_text(tg_user_id: int) -> str:
    async with async_session_factory() as session:
        auth_stmt = select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.tg_user_id == tg_user_id)
        auth = (await session.execute(auth_stmt)).scalar_one_or_none()
        profile = await session.get(SpecialistProfile, auth.specialist_id) if auth is not None else None

        purchase = await get_latest_billing_purchase_for_tg_user(session, tg_user_id)

    if profile is None:
        if purchase is None:
            return "Статус подписки: не найден профиль специалиста."
        return (
            f"Статус подписки: профиль не найден. Последний заказ {purchase.plan.value}/{purchase.period.value}, "
            f"статус {purchase.status.value}."
        )

    plan = profile.tariff_plan.value if isinstance(profile.tariff_plan, TariffPlan) else str(profile.tariff_plan)
    period = profile.tariff_period if isinstance(profile.tariff_period, BillingPeriod) else None
    period_label = _PERIOD_LABELS.get(period, "—")
    paid_until = profile.tariff_paid_until.isoformat() if profile.tariff_paid_until else "—"

    return (
        "Статус подписки:\n"
        f"• План: {plan}\n"
        f"• Период: {period_label}\n"
        f"• Активна до: {paid_until}"
    )
