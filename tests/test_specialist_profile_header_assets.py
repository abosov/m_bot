from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sticky_header_css_and_runtime_offset_present():
    css = (ROOT / "frontend/styles/specialist.css").read_text(encoding="utf-8")
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert "position: sticky;" in css
    assert "top: 0;" in css
    assert "z-index: 100;" in css
    assert ".specialist-page" in css
    assert "padding-top: var(--specialist-header-height);" not in css
    assert "scroll-padding-top: var(--specialist-sticky-offset, 120px);" in css
    assert "scroll-margin-top: var(--specialist-sticky-offset, 120px);" in css
    assert 'className="specialist-page"' in page
    assert 'document.getElementById("specialist-sticky-header")' in page
    assert 'document.documentElement.style.setProperty("--specialist-sticky-offset", offset);' in page


def test_header_contains_identity_and_navigation_items():
    header = (ROOT / "frontend/components/specialist/Header.tsx").read_text(encoding="utf-8")

    assert "displayName" in header
    assert "specialization" in header
    assert "О себе" in header
    assert "Образование" in header
    assert "Документы" in header
    assert "Услуги и цены" in header
    assert "Отзывы" in header
    assert "Записаться" in header


def test_anchor_links_match_page_sections():
    header = (ROOT / "frontend/components/specialist/Header.tsx").read_text(encoding="utf-8")
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")
    about = (ROOT / "frontend/components/specialist/SectionAbout.tsx").read_text(encoding="utf-8")
    education = (ROOT / "frontend/components/specialist/SectionEducation.tsx").read_text(encoding="utf-8")
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")
    documents = (ROOT / "frontend/components/specialist/SectionDocuments.tsx").read_text(encoding="utf-8")
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")
    cta = (ROOT / "frontend/components/specialist/SectionCTA.tsx").read_text(encoding="utf-8")

    for anchor in ("about", "education", "documents", "services", "reviews", "booking"):
        assert f'"#{anchor}"' in header
        if anchor == "about":
            assert f'id="{anchor}"' in about
        elif anchor == "education":
            assert f'id="{anchor}"' in education
        elif anchor == "reviews":
            assert f'id="{anchor}"' in reviews
        elif anchor == "services":
            assert f'id="{anchor}"' in services
        elif anchor == "booking":
            assert f'id="{anchor}"' in cta
        elif anchor == "documents":
            assert f'id="{anchor}"' in documents
        else:
            assert f'id="{anchor}"' in page



def test_public_page_section_render_order_matches_editor_flow():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    hero_idx = page.index("<Hero")
    about_idx = page.index("<SectionAbout")
    education_idx = page.index("<SectionEducation")
    documents_idx = page.index("<SectionDocuments")
    services_idx = page.index("<SectionServices")
    reviews_idx = page.index("<SectionReviews")

    assert hero_idx < about_idx < education_idx < documents_idx < services_idx < reviews_idx
