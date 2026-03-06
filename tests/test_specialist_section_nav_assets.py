from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_section_nav_component_has_accessible_wrapper_and_active_tracking():
    nav = (ROOT / "frontend/components/specialist/SectionNav.tsx").read_text(encoding="utf-8")

    assert 'id="specialist-section-nav"' in nav
    assert 'aria-label="Навигация по разделам специалиста"' in nav
    assert "IntersectionObserver" in nav
    assert "specialist-subnav__link--active" in nav
    assert "scrollIntoView({ behavior: \"smooth\", block: \"start\" })" in nav


def test_section_nav_supports_booking_cta_and_mobile_scroll_list():
    nav = (ROOT / "frontend/components/specialist/SectionNav.tsx").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles/specialist.css").read_text(encoding="utf-8")

    assert "specialist-subnav__cta" in nav
    assert ".specialist-subnav__list" in css
    assert "overflow-x: auto;" in css
    assert "scrollbar-width: none;" in css
