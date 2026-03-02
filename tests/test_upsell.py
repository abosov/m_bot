from datetime import datetime, timezone

import pytest

from database import TariffPlan
from services.upsell import maybe_mark_analytics_upsell_needed


class _Session:
    def __init__(self, monthly_count: int):
        self.monthly_count = monthly_count

    async def scalar(self, _stmt):
        return self.monthly_count


@pytest.mark.asyncio
async def test_upsell_is_triggered_for_free_after_70_percent() -> None:
    profile = type(
        "Profile",
        (),
        {
            "tariff_plan": TariffPlan.free,
            "analytics_upsell_prompted_at": None,
        },
    )()

    session = _Session(monthly_count=12)
    now_utc = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)

    triggered = await maybe_mark_analytics_upsell_needed(
        session=session,
        profile=profile,
        specialist_id="sp-1",
        now_utc=now_utc,
    )

    assert triggered is True
    assert profile.analytics_upsell_prompted_at == now_utc


@pytest.mark.asyncio
async def test_upsell_is_not_triggered_more_than_once_per_month() -> None:
    now_utc = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    profile = type(
        "Profile",
        (),
        {
            "tariff_plan": TariffPlan.start,
            "analytics_upsell_prompted_at": datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        },
    )()

    session = _Session(monthly_count=100)

    triggered = await maybe_mark_analytics_upsell_needed(
        session=session,
        profile=profile,
        specialist_id="sp-1",
        now_utc=now_utc,
    )

    assert triggered is False
