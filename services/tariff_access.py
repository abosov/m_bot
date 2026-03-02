from __future__ import annotations

from database import TariffPlan

ANALYTICS_PRO_REQUIRED_ERROR = "Аналитика доступна на тарифе Pro и выше."


class AnalyticsAccessError(PermissionError):
    pass


def has_analytics_access(plan: TariffPlan | str | None) -> bool:
    if plan is None:
        return False
    value = plan.value if isinstance(plan, TariffPlan) else str(plan)
    return value in {TariffPlan.pro.value, TariffPlan.team.value}


def ensure_analytics_access(plan: TariffPlan | str | None) -> None:
    if not has_analytics_access(plan):
        raise AnalyticsAccessError(ANALYTICS_PRO_REQUIRED_ERROR)
