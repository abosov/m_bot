from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_about_section_uses_about_block_and_hides_when_missing():
    about = (ROOT / "frontend/components/specialist/SectionAbout.tsx").read_text(encoding="utf-8")

    assert 'block.block_type === "about"' in about
    assert "if (!aboutBlock)" in about
    assert "return null;" in about


def test_about_section_sanitizes_html_before_render():
    about = (ROOT / "frontend/components/specialist/SectionAbout.tsx").read_text(encoding="utf-8")

    assert "function sanitizeHtml" in about
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in about
    assert "replace(/\\son\\w+=" in about
    assert "replace(/javascript:/gi, \"\")" in about
    assert "dangerouslySetInnerHTML" in about


def test_page_uses_section_about_component_with_blocks_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionAbout from "../components/specialist/SectionAbout";' in page
    assert "<SectionAbout blocks={payload?.blocks} />" in page
