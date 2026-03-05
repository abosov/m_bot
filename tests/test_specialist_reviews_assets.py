from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reviews_section_supports_multiple_reviews_cards():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert "normalizedReviews.map" in reviews
    assert "<article" in reviews
    assert "review.authorName" in reviews
    assert "review.content" in reviews


def test_reviews_section_hides_when_no_reviews():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert "if (!normalizedReviews.length)" in reviews
    assert "return null;" in reviews


def test_reviews_section_sanitizes_author_and_content():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert "function sanitizeHtml" in reviews
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in reviews
    assert "replace(/\\son\\w+=" in reviews
    assert "replace(/javascript:/gi, \"\")" in reviews


def test_page_uses_section_reviews_component_with_reviews_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionReviews from "../components/specialist/SectionReviews";' in page
    assert "<SectionReviews reviews={payload?.reviews} />" in page
