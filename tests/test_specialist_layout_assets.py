from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SECTION_FILES = [
    "frontend/components/specialist/SectionAbout.tsx",
    "frontend/components/specialist/SectionEducation.tsx",
    "frontend/components/specialist/SectionDocuments.tsx",
    "frontend/components/specialist/SectionServices.tsx",
    "frontend/components/specialist/SectionReviews.tsx",
    "frontend/components/specialist/SectionCTA.tsx",
]


def test_layout_css_has_shared_container_section_and_card():
    layout_css = (ROOT / "frontend/styles/layout.css").read_text(encoding="utf-8")

    assert ".container" in layout_css
    assert "max-width: 1100px;" in layout_css
    assert ".section" in layout_css
    assert "padding-top: 72px;" in layout_css
    assert "padding-bottom: 72px;" in layout_css
    assert ".section-card" in layout_css
    assert "padding: 48px;" in layout_css
    assert "@media (max-width: 767px)" in layout_css
    assert "padding: 28px;" in layout_css


def test_all_public_sections_use_unified_layout_wrappers():
    for file_path in SECTION_FILES:
        content = (ROOT / file_path).read_text(encoding="utf-8")
        assert "className=\"specialist-page__section section\"" in content
        assert "className=\"container\"" in content
        assert "className=\"section-card" in content


def test_bridge_public_slug_page_uses_layout_classes_without_inline_hero_styles():
    web_server = (ROOT / "web_server.py").read_text(encoding="utf-8")

    assert 'id="public-specialist-hero-grid" class="section-card specialist-hero hero-grid specialist-card"' in web_server
    assert 'id="public-specialist-hero-photo-image" class="specialist-hero__photo specialist-hidden"' in web_server
    assert 'id="public-specialist-hero-quote" class="specialist-hero__quote hero-quote specialist-hidden"' in web_server
    assert 'id="specialist-contacts" class="specialist-contacts specialist-hidden"' in web_server
