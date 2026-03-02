from datetime import datetime, timezone

import pytest

from database import TariffPlan
from services.plan_limits import (
    FREE_PLAN_LIMIT_REACHED_ERROR,
    PlanLimitError,
    enforce_booking_plan_limit,
)


class _Session:
    def __init__(self, monthly_count: int):
        self.monthly_count = monthly_count

    async def scalar(self, _stmt):
        return self.monthly_count


@pytest.mark.asyncio
async def test_enforce_booking_plan_limit_skips_non_free_plan() -> None:
    session = _Session(monthly_count=999)
    profile = type("Profile", (), {"tariff_plan": TariffPlan.start})()

    await enforce_booking_plan_limit(
        session=session,
        profile=profile,
        specialist_id="sp-1",
        slot_start_utc=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_enforce_booking_plan_limit_raises_for_free_when_limit_reached() -> None:
    session = _Session(monthly_count=16)
    profile = type("Profile", (), {"tariff_plan": TariffPlan.free})()

    with pytest.raises(PlanLimitError, match="лимита бесплатного тарифа") as exc_info:
        await enforce_booking_plan_limit(
            session=session,
            profile=profile,
            specialist_id="sp-1",
            slot_start_utc=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        )

    assert str(exc_info.value) == FREE_PLAN_LIMIT_REACHED_ERROR
