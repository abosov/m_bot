import pytest

from services.tariff_access import ANALYTICS_PRO_REQUIRED_ERROR, AnalyticsAccessError, ensure_analytics_access, has_analytics_access


def test_has_analytics_access_only_for_pro_and_team() -> None:
    assert has_analytics_access("free") is False
    assert has_analytics_access("start") is False
    assert has_analytics_access("pro") is True
    assert has_analytics_access("team") is True


def test_ensure_analytics_access_raises_for_start() -> None:
    with pytest.raises(AnalyticsAccessError) as exc_info:
        ensure_analytics_access("start")

    assert str(exc_info.value) == ANALYTICS_PRO_REQUIRED_ERROR
