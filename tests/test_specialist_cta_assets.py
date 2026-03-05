from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cta_generates_booking_link_with_required_template():
    cta = (ROOT / "frontend/components/specialist/SectionCTA.tsx").read_text(encoding="utf-8")

    assert "buildClientBotBookingLink" in cta
    assert "https://t.me/${clientBotUsername}?start=book_${specialistId}" in cta
    assert "Записаться на консультацию" in cta


def test_cta_validates_bot_username_and_hides_on_invalid_data():
    cta = (ROOT / "frontend/components/specialist/SectionCTA.tsx").read_text(encoding="utf-8")

    assert "TELEGRAM_BOT_USERNAME_REGEX" in cta
    assert "Number.isInteger(specialistId) && specialistId > 0" in cta
    assert "if (!bookingLink)" in cta
    assert "return null;" in cta


def test_page_uses_section_cta_component_with_profile_data():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionCTA from "../components/specialist/SectionCTA";' in page
    assert "clientBotUsername={payload?.profile.client_bot_username as string | undefined}" in page
    assert "specialistId={payload?.profile.specialist_id as number | undefined}" in page
