from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from database import GoogleOAuthStatus, TariffPlan
from services.referrals import extract_referral_code, process_referral_activation


def test_extract_referral_code_supports_prefix() -> None:
    assert extract_referral_code("ref_ab-12") == "AB12"
    assert extract_referral_code(" zz99 ") == "ZZ99"


@pytest.mark.asyncio
async def test_process_referral_activation_applies_start_bonus_for_free_referrer() -> None:
    referrer_id = uuid4()
    referred_id = uuid4()

    referrer = SimpleNamespace(specialist_id=referrer_id)
    referred = SimpleNamespace(
        specialist_id=referred_id,
        referrer_id=referrer_id,
        referral_bonus_awarded_at=None,
    )
    referrer_profile = SimpleNamespace(
        tariff_plan=TariffPlan.free,
        start_bonus_until=None,
        referral_bonus_months=0,
    )

    class _Session:
        async def get(self, model, pk):
            name = model.__name__
            if name == "Specialist" and pk == referred_id:
                return referred
            if name == "Specialist" and pk == referrer_id:
                return referrer
            if name == "SpecialistProfile" and pk == referrer_id:
                return referrer_profile
            return None

        async def scalar(self, _stmt):
            return 1

    changed = await process_referral_activation(_Session(), referred_id)

    assert changed is True
    assert referrer_profile.tariff_plan == TariffPlan.start
    assert referrer_profile.referral_bonus_months == 1
    assert referrer_profile.start_bonus_until is not None
    assert referred.referral_bonus_awarded_at is not None


@pytest.mark.asyncio
async def test_process_referral_activation_does_not_apply_for_pro_referrer() -> None:
    referrer_id = uuid4()
    referred_id = uuid4()

    referrer = SimpleNamespace(specialist_id=referrer_id)
    referred = SimpleNamespace(
        specialist_id=referred_id,
        referrer_id=referrer_id,
        referral_bonus_awarded_at=None,
    )
    referrer_profile = SimpleNamespace(
        tariff_plan=TariffPlan.pro,
        start_bonus_until=None,
        referral_bonus_months=2,
    )

    class _Session:
        async def get(self, model, pk):
            name = model.__name__
            if name == "Specialist" and pk == referred_id:
                return referred
            if name == "Specialist" and pk == referrer_id:
                return referrer
            if name == "SpecialistProfile" and pk == referrer_id:
                return referrer_profile
            return None

        async def scalar(self, _stmt):
            return 1

    changed = await process_referral_activation(_Session(), referred_id)

    assert changed is True
    assert referrer_profile.tariff_plan == TariffPlan.pro
    assert referrer_profile.referral_bonus_months == 3
    assert referrer_profile.start_bonus_until is None
