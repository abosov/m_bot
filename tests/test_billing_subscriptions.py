import types
from datetime import datetime, timezone

import pytest

from services.billing import subscriptions


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
