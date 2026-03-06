from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reviews_section_extracts_reviews_from_blocks_payload():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert 'block.block_type === "reviews"' in reviews
    assert "reviewsBlock.items ?? reviewsBlock.content ?? reviewsBlock.body ?? reviewsBlock.text" in reviews


def test_reviews_section_renders_cards_grid_classes():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert 'className="reviews-grid"' in reviews
    assert 'className="review-card"' in reviews
    assert 'className="review-text"' in reviews
    assert 'className="review-author"' in reviews


def test_reviews_section_hides_when_reviews_block_is_empty_or_missing():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert "if (!reviewItems.length)" in reviews
    assert "return null;" in reviews


def test_reviews_section_sanitizes_reviews_content():
    reviews = (ROOT / "frontend/components/specialist/SectionReviews.tsx").read_text(encoding="utf-8")

    assert "function sanitizeText" in reviews
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in reviews
    assert "replace(/\\son\\w+=" in reviews
    assert "replace(/javascript:/gi, \"\")" in reviews


def test_bridge_runtime_renders_reviews_cards():
    bridge = (ROOT / "web_server.py").read_text(encoding="utf-8")

    assert "const renderReviews = (blocks) =>" in bridge
    assert "listEl.className = 'reviews-grid';" in bridge
    assert "card.className = 'review-card';" in bridge
    assert "text.className = 'review-text';" in bridge
    assert "author.className = 'review-author';" in bridge


def test_page_uses_section_reviews_component_with_blocks_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionReviews from "../components/specialist/SectionReviews";' in page
    assert "<SectionReviews blocks={payload?.blocks} />" in page


def test_page_keeps_reviews_payload_field_for_backward_compatibility():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert "reviews: Array<Record<string, unknown>>;" in page
