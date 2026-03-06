from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hero_grid_layout_and_contact_cta_present():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert 'className="section-card specialist-card specialist-hero hero-grid"' in hero
    assert 'className="specialist-hero__photo-wrap profile-photo"' in hero
    assert "Связаться со специалистом" in hero


def test_hero_quote_conditional_render_and_allowed_domains_guard_present():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert 'const quoteText = (heroQuote ?? "").trim();' in hero
    assert 'const hasQuote = quoteText.length > 0;' in hero
    assert '{hasQuote ? <blockquote className="specialist-hero__quote hero-quote">{quoteText}</blockquote> : null}' in hero
    assert 'const ALLOWED_IMAGE_HOSTNAMES = new Set(["images.mbot.app", "cdn.mbot.app"]);' in hero
    assert "ALLOWED_IMAGE_HOSTNAMES.has(url.hostname)" in hero
    assert "Фото специалиста недоступно" in hero


def test_client_bot_link_uses_profile_uuid_payload_when_available():
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")
    links = (ROOT / "frontend/utils/telegram_links.ts").read_text(encoding="utf-8")

    assert 'buildClientBotLink(clientBotUsername, "contact_specialist", specialistUuid)' in hero
    assert "UUID_REGEX" in links
    assert "actionPayload = normalizedSpecialistUuid ? `${action}_${normalizedSpecialistUuid}` : action" in links


def test_contacts_component_renders_only_non_empty_and_valid_email():
    contacts = (ROOT / "frontend/components/specialist/Contacts.tsx").read_text(encoding="utf-8")
    hero = (ROOT / "frontend/components/specialist/Hero.tsx").read_text(encoding="utf-8")

    assert "BASIC_EMAIL_REGEX" in contacts
    assert "normalizeValue" in contacts
    assert "isValidEmail" in contacts
    assert 'normalizedTelegram ? { id: "telegram", label: "Telegram", value: normalizedTelegram } : null' in contacts
    assert 'normalizedWhatsapp ? { id: "whatsapp", label: "WhatsApp", value: normalizedWhatsapp } : null' in contacts
    assert 'normalizedPhone ? { id: "phone", label: "Телефон", value: normalizedPhone } : null' in contacts
    assert 'normalizedEmail ? { id: "email", label: "Email", value: normalizedEmail } : null' in contacts
    assert '<Contacts telegram={telegram} whatsapp={whatsapp} phone={phone} email={email} />' in hero


def test_page_maps_nested_contacts_to_hero_props():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert "export function mapProfileToHeroContacts" in page
    assert "telegram: profile?.contacts?.telegram ?? undefined" in page
    assert "whatsapp: profile?.contacts?.whatsapp ?? undefined" in page
    assert "phone: profile?.contacts?.phone ?? undefined" in page
    assert "email: profile?.contacts?.email ?? undefined" in page
    assert "profile.contact_telegram" not in page
    assert "profile.contact_whatsapp" not in page
    assert "profile.contact_phone" not in page
    assert "profile.contact_email" not in page
