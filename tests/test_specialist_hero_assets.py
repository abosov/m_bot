from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hero_grid_layout_and_contact_cta_present():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert 'gridTemplateAreas: ' in hero
    assert '"photo quote" "photo button"' in hero
    assert "Связаться со специалистом" in hero


def test_hero_quote_fallback_and_allowed_domains_guard_present():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert 'heroQuote ?? ""' in hero
    assert 'const ALLOWED_IMAGE_HOSTNAMES = new Set(["images.mbot.app", "cdn.mbot.app"]);' in hero
    assert "ALLOWED_IMAGE_HOSTNAMES.has(url.hostname)" in hero
    assert "Фото специалиста недоступно" in hero


def test_client_bot_link_template_and_username_validation_present():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert "TELEGRAM_BOT_USERNAME_REGEX" in hero
    assert "UUID_REGEX" in hero
    assert "buildClientBotWriteLink" in hero
    assert "https://t.me/${clientBotUsername}?start=write_${specialistId}" in hero
    assert "UUID_REGEX.test(specialistId)" in hero


def test_contacts_component_renders_only_non_empty_and_valid_email():
    contacts = (ROOT / "frontend/components/specialist/Contacts.tsx").read_text(encoding="utf-8")
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert "BASIC_EMAIL_REGEX" in contacts
    assert "normalizeValue" in contacts
    assert "isValidEmail" in contacts
    assert "{normalizedTelegram ? <p>Telegram:" in contacts
    assert "{normalizedWhatsapp ? <p>WhatsApp:" in contacts
    assert "{normalizedPhone ? <p>Телефон:" in contacts
    assert "{normalizedEmail ? <p>Email:" in contacts
    assert '<Contacts telegram={telegram} whatsapp={whatsapp} phone={phone} email={email} />' in hero


def test_page_passes_contacts_to_hero():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert "telegram={payload?.profile.contact_telegram as string | undefined}" in page
    assert "whatsapp={payload?.profile.contact_whatsapp as string | undefined}" in page
    assert "phone={payload?.profile.contact_phone as string | undefined}" in page
    assert "email={payload?.profile.contact_email as string | undefined}" in page
