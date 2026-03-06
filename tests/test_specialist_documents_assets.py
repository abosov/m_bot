from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_documents_section_filters_document_media_and_renders_section():
    documents = (ROOT / "frontend/components/specialist/SectionDocuments.tsx").read_text(encoding="utf-8")

    assert 'raw.media_type' in documents
    assert 'mediaType !== "document"' in documents
    assert 'id="documents"' in documents


def test_documents_section_is_hidden_when_no_document_media():
    documents = (ROOT / "frontend/components/specialist/SectionDocuments.tsx").read_text(encoding="utf-8")

    assert "if (!documentItems.length)" in documents
    assert "return null;" in documents


def test_documents_with_null_url_render_title_without_fake_link():
    documents = (ROOT / "frontend/components/specialist/SectionDocuments.tsx").read_text(encoding="utf-8")

    assert "normalizeUrl" in documents
    assert "if (!/^https?:\\/\\//i.test(sanitized))" in documents
    assert "{item.url ? (" in documents
    assert "<span>{item.title}</span>" in documents


def test_page_passes_media_to_documents_section_component():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionDocuments from "../components/specialist/SectionDocuments";' in page
    assert "<SectionDocuments media={payload?.media} />" in page
