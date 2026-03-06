from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_education_section_uses_education_block_and_hides_when_missing():
    education = (ROOT / "frontend/components/specialist/SectionEducation.tsx").read_text(encoding="utf-8")

    assert 'block.block_type === "education"' in education
    assert "if (!educationBlock)" in education
    assert "if (!educationItems.length)" in education
    assert "return null;" in education


def test_education_section_renders_list_and_sanitizes_content():
    education = (ROOT / "frontend/components/specialist/SectionEducation.tsx").read_text(encoding="utf-8")

    assert "<ul className=" in education
    assert "<li" in education
    assert "function sanitizeHtml" in education
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in education
    assert "replace(/\\son\\w+=" in education
    assert "replace(/javascript:/gi, \"\")" in education


def test_page_uses_section_education_component_with_blocks_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionEducation from "../components/specialist/SectionEducation";' in page
    assert "<SectionEducation blocks={payload?.blocks} />" in page
