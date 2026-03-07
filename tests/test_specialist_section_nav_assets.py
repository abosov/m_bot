from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_section_nav_component_has_accessible_wrapper_and_geometry_based_active_tracking():
    nav = (ROOT / "frontend/components/specialist/SectionNav.tsx").read_text(encoding="utf-8")

    assert 'id="specialist-section-nav"' in nav
    assert 'aria-label="Навигация по разделам специалиста"' in nav
    assert "IntersectionObserver" in nav
    assert 'import { resolveActiveSectionId } from "./sectionNavActiveResolver"' in nav
    assert "resolveActiveSectionId" in nav
    assert "sectionGeometries" in nav
    assert "section.trackingTarget.getBoundingClientRect().top + window.scrollY" in nav
    assert 'rootMargin: "-10% 0px -40% 0px"' in nav
    assert "specialist-subnav__link--active" in nav
    assert "window.addEventListener(\"scroll\", scheduleUpdate, { passive: true })" in nav
    assert "resolveTrackingTarget" in nav
    assert 'section.querySelector<HTMLElement>(".section-card")' in nav
    assert 'section.querySelector<HTMLElement>("h2.section-title")' in nav


def test_section_nav_keeps_smooth_scroll_only_for_user_click_and_mobile_list_is_scrollable():
    nav = (ROOT / "frontend/components/specialist/SectionNav.tsx").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles/specialist.css").read_text(encoding="utf-8")

    assert 'target.scrollIntoView({ behavior: "smooth", block: "start" })' in nav
    assert 'scrollIntoView({ inline: "center", block: "nearest", behavior: "auto" })' in nav
    assert ".specialist-subnav__list" in css
    assert "overflow-x: auto;" in css
    assert "scrollbar-width: none;" in css
