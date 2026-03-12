import types
from datetime import datetime, timezone

import pytest

from database import BillingPaymentStatus
from services.billing import subscriptions
from services.integrations import yookassa_client


@pytest.mark.asyncio
async def test_yookassa_client_create_payment_maps_request(monkeypatch):
    captured = {}

    class _Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "id": "yk-pay-1",
                "status": "pending",
                "confirmation": {"confirmation_url": "https://pay.example/confirm"},
            }

    class _AsyncClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Response()

    monkeypatch.setattr(yookassa_client.config, "YOOKASSA_SHOP_ID", "shop-id")
    monkeypatch.setattr(yookassa_client.config, "YOOKASSA_SECRET_KEY", "secret-key")
    monkeypatch.setattr(yookassa_client.httpx, "AsyncClient", _AsyncClient)

    client = yookassa_client.YooKassaClient()
    response = await client.create_payment(
        amount_minor=99000,
        currency="RUB",
        description="Zumbot subscription pro-monthly",
        return_url="https://example.test/return",
        idempotence_key="idem-123",
        metadata={"payment_id": "payment-1"},
    )

    assert response["id"] == "yk-pay-1"
    assert captured["url"].endswith("/payments")
    assert captured["json"]["amount"] == {"value": "990.00", "currency": "RUB"}
    assert captured["json"]["metadata"] == {"payment_id": "payment-1"}
    assert captured["headers"]["Idempotence-Key"] == "idem-123"


@pytest.mark.asyncio
async def test_create_yookassa_payment_for_token_invalid_token(monkeypatch):
    async def _fake_get(_token):
        return None

    monkeypatch.setattr(subscriptions, "get_purchase_for_raw_token", _fake_get)

    with pytest.raises(subscriptions.BillingError, match="invalid_token"):
        await subscriptions.create_yookassa_payment_for_token("bad-token")


@pytest.mark.asyncio
async def test_process_yookassa_webhook_invalid_payload():
    with pytest.raises(subscriptions.BillingError, match="invalid_payload"):
        await subscriptions.process_yookassa_webhook({"event": "payment.succeeded"})


@pytest.mark.asyncio
async def test_create_billing_payment_intent_retryable_error_keeps_new_status(monkeypatch):
    payment = types.SimpleNamespace(
        payment_id="payment-1",
        specialist_id="specialist-1",
        amount_minor=99000,
        currency="RUB",
        description="Zumbot subscription pro-monthly",
        return_url="https://example.test/return",
        tariff_id="tariff-1",
        subscription_id=None,
        provider=subscriptions.BillingProvider.yookassa,
        provider_idempotence_key="billing-payment:payment-1",
        provider_payment_id=None,
        confirmation_url=None,
        metadata_json=None,
        status=BillingPaymentStatus.new,
    )
    tariff = types.SimpleNamespace(code="pro-monthly")

    class _Session:
        async def get(self, model, obj_id):
            if model is subscriptions.BillingPayment:
                assert obj_id == "payment-1"
                return payment
            if model is subscriptions.BillingTariff:
                return tariff
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _Client:
        async def create_payment(self, **_kwargs):
            raise subscriptions.YooKassaClientNetworkError("timeout")

    monkeypatch.setattr(subscriptions, "async_session_factory", lambda: _Session())

    result = await subscriptions.create_billing_payment_intent(
        specialist_id="specialist-1",
        tariff_id="tariff-1",
        return_url="https://example.test/return",
        payment_id="payment-1",
        client=_Client(),
    )

    assert result.outcome == "retryable_error"
    assert result.status == BillingPaymentStatus.new
    assert payment.status == BillingPaymentStatus.new


def test_hash_pay_token_is_deterministic():
    a = subscriptions.hash_pay_token("abc")
    b = subscriptions.hash_pay_token("abc")
    c = subscriptions.hash_pay_token("xyz")
    assert a == b
    assert a != c


@pytest.mark.asyncio
async def test_get_latest_purchase_status_text_includes_plan_period_until(monkeypatch):
    profile = types.SimpleNamespace(
        tariff_plan=subscriptions.TariffPlan.pro,
        tariff_period=subscriptions.BillingPeriod.yearly,
        tariff_paid_until=datetime(2027, 1, 1, tzinfo=timezone.utc),
    )

    class _Session:
        async def execute(self, _stmt):
            auth = types.SimpleNamespace(specialist_id="sp-1")
            return types.SimpleNamespace(scalar_one_or_none=lambda: auth)

        async def get(self, _model, _specialist_id):
            return profile

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(subscriptions, "async_session_factory", lambda: _Session())

    async def _fake_latest(_session, _tg_user_id):
        return None

    monkeypatch.setattr(subscriptions, "get_latest_billing_purchase_for_tg_user", _fake_latest)

    text = await subscriptions.get_latest_purchase_status_text(123)
    assert "Статус подписки" in text
    assert "План: pro" in text
    assert "Период: год" in text
    assert "Активна до:" in text
