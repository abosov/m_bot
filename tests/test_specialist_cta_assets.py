from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cta_uses_common_telegram_link_builder_and_label():
    cta = (ROOT / "frontend/components/specialist/SectionCTA.tsx").read_text(encoding="utf-8")

    assert "buildClientBotLink" in cta
    assert 'buildClientBotLink(clientBotUsername, "book", specialistUuid)' in cta
    assert "Записаться на консультацию" in cta


def test_cta_hides_when_link_cannot_be_built():
    cta = (ROOT / "frontend/components/specialist/SectionCTA.tsx").read_text(encoding="utf-8")

    assert "if (!bookingLink)" in cta
    assert "return null;" in cta


def test_page_uses_section_cta_with_profile_id_uuid():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionCTA from "../components/specialist/SectionCTA";' in page
    assert "const specialistUuid = payload?.profile.id;" in page
    assert "<SectionCTA clientBotUsername={clientBotUsername} specialistUuid={specialistUuid} />" in page
