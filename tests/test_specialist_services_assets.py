from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_services_section_uses_services_block_and_renders_cards():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert 'block.block_type === "services"' in services
    assert 'className="services-grid"' in services
    assert 'className="service-card"' in services
    assert 'className="service-title"' in services
    assert 'className="service-price"' in services
    assert 'className="service-description"' in services
    assert 'className="service-cta"' in services


def test_services_section_sanitizes_text():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert "function sanitizeText" in services
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in services
    assert "replace(/\\son\\w+=" in services
    assert "replace(/javascript:/gi, \"\")" in services


def test_services_section_hides_when_no_items():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert "if (!servicesBlock)" in services
    assert "if (!serviceItems.length)" in services
    assert "return null;" in services


def test_page_uses_section_services_component_with_blocks_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionServices from "../components/specialist/SectionServices";' in page
    assert "<SectionServices blocks={payload?.blocks} />" in page


def test_bridge_runtime_renders_services_cards():
    bridge = (ROOT / "web_server.py").read_text(encoding="utf-8")

    assert "const renderServices = (blocks, bookingHref) =>" in bridge
    assert "listEl.className = 'services-grid';" in bridge
    assert "card.className = 'service-card';" in bridge
    assert "ctaWrap.className = 'service-cta';" in bridge
