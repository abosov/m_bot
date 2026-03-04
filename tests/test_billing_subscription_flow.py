from datetime import datetime, timedelta, timezone
import types

import pytest
from fastapi.testclient import TestClient

import web_server
from database import BillingPeriod, BillingPurchaseStatus, TariffPlan
from services.billing import subscriptions


class _DummySessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_create_purchase_stores_only_hash_and_returns_pay_url(monkeypatch):
    captured = {}

    class _Session:
        def add(self, obj):
            captured["purchase"] = obj

        async def commit(self):
            captured["committed"] = True

    monkeypatch.setattr(subscriptions, "async_session_factory", lambda: _DummySessionCtx(_Session()))

    raw_token, pay_url = await subscriptions.create_subscription_purchase(
        specialist_id="00000000-0000-0000-0000-000000000111",
        tg_user_id=123456,
        plan=TariffPlan.pro,
        period=BillingPeriod.monthly,
    )

    assert pay_url.endswith(f"/pay?token={raw_token}")
    purchase = captured["purchase"]
    assert purchase.pay_token_hash != raw_token
    assert raw_token not in purchase.pay_token_hash
    assert purchase.status == BillingPurchaseStatus.pending


def test_pay_page_returns_200_for_valid_token(monkeypatch):
    now = datetime.now(timezone.utc)
    purchase = types.SimpleNamespace(
        expires_at=now + timedelta(minutes=5),
        used_at=None,
        plan=TariffPlan.start,
        period=BillingPeriod.monthly,
        amount_rub_int=990,
    )

    async def _fake_get_purchase(_token):
        return purchase

    monkeypatch.setattr(web_server, "get_purchase_for_raw_token", _fake_get_purchase)

    client = TestClient(web_server.app)
    response = client.get("/pay", params={"token": "valid-token-1234567890"})

    assert response.status_code == 200
    assert "Заказ на подписку Zumbot" in response.text


def test_pay_page_returns_404_for_missing_token(monkeypatch):
    async def _fake_get_purchase(_token):
        return None

    monkeypatch.setattr(web_server, "get_purchase_for_raw_token", _fake_get_purchase)

    client = TestClient(web_server.app)
    response = client.get("/pay", params={"token": "missing-token-123456"})

    assert response.status_code == 404


def test_pay_page_returns_410_for_expired_or_used(monkeypatch):
    now = datetime.now(timezone.utc)
    expired = types.SimpleNamespace(
        expires_at=now - timedelta(seconds=1),
        used_at=None,
        plan=TariffPlan.start,
        period=BillingPeriod.monthly,
        amount_rub_int=990,
    )
    used = types.SimpleNamespace(
        expires_at=now + timedelta(minutes=5),
        used_at=now,
        plan=TariffPlan.start,
        period=BillingPeriod.monthly,
        amount_rub_int=990,
    )

    state = {"obj": expired}

    async def _fake_get_purchase(_token):
        return state["obj"]

    monkeypatch.setattr(web_server, "get_purchase_for_raw_token", _fake_get_purchase)

    client = TestClient(web_server.app)

    response_expired = client.get("/pay", params={"token": "expired-token-123456"})
    assert response_expired.status_code == 410

    state["obj"] = used
    response_used = client.get("/pay", params={"token": "used-token-123456789"})
    assert response_used.status_code == 410


@pytest.mark.asyncio
async def test_webhook_succeeded_is_idempotent_and_updates_profile(monkeypatch):
    now = datetime.now(timezone.utc)
    purchase = types.SimpleNamespace(
        purchase_id="purchase-1",
        specialist_id="specialist-1",
        plan=TariffPlan.pro,
        period=BillingPeriod.yearly,
        status=BillingPurchaseStatus.awaiting_payment,
        used_at=None,
    )
    profile = types.SimpleNamespace(
        tariff_plan=TariffPlan.start,
        tariff_period=None,
        tariff_last_paid_at=None,
        tariff_paid_until=None,
    )

    class _Session:
        async def get(self, model, specialist_id):
            assert specialist_id == "specialist-1"
            return profile

        async def commit(self):
            return None

    async def _fake_get_purchase_by_payment_id(_session, payment_id):
        assert payment_id == "yk-payment-1"
        return purchase

    async def _fake_set_yk_fields(_session, _purchase_id, **_kwargs):
        return None

    async def _fake_set_status(_session, _purchase_id, status):
        purchase.status = status

    monkeypatch.setattr(subscriptions, "async_session_factory", lambda: _DummySessionCtx(_Session()))
    monkeypatch.setattr(subscriptions, "get_billing_purchase_by_yookassa_payment_id", _fake_get_purchase_by_payment_id)
    monkeypatch.setattr(subscriptions, "set_billing_purchase_yookassa_fields", _fake_set_yk_fields)
    monkeypatch.setattr(subscriptions, "set_billing_purchase_status", _fake_set_status)

    payload = {"object": {"id": "yk-payment-1", "status": "succeeded"}}

    first_status = await subscriptions.process_yookassa_webhook(payload)
    first_paid_until = profile.tariff_paid_until
    first_last_paid_at = profile.tariff_last_paid_at

    second_status = await subscriptions.process_yookassa_webhook(payload)

    assert first_status == "succeeded"
    assert second_status == "succeeded"
    assert purchase.status == BillingPurchaseStatus.succeeded
    assert profile.tariff_plan == TariffPlan.pro
    assert profile.tariff_period == BillingPeriod.yearly
    assert profile.tariff_paid_until == first_paid_until
    assert profile.tariff_last_paid_at == first_last_paid_at


@pytest.mark.asyncio
async def test_raw_token_not_logged_on_invalid_create_payment(monkeypatch, caplog):
    raw_token = "raw-sensitive-token-123"

    async def _fake_get(_token):
        return None

    monkeypatch.setattr(subscriptions, "get_purchase_for_raw_token", _fake_get)

    with pytest.raises(subscriptions.BillingError):
        await subscriptions.create_yookassa_payment_for_token(raw_token)

    assert raw_token not in caplog.text
