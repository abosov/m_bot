from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_services_section_uses_services_block_and_renders_list_rows():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert 'block.block_type === "services"' in services
    assert 'className="specialist-list"' in services
    assert 'className="specialist-list__item specialist-list__item--service"' in services
    assert 'className="specialist-service__price"' in services
    assert 'function buildServiceLabel(item: ServiceItem): string' in services
    assert 'return `${name} — ${description}`;' in services
    assert '.filter((item) => item.label.length > 0);' in services
    assert 'Записаться' not in services


def test_services_section_sanitizes_text():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert "function sanitizeText" in services
    assert "<script[\\s\\S]*?>[\\s\\S]*?<\\/script>" in services
    assert "replace(/\\son\\w+=" in services
    assert "replace(/javascript:/gi, \"\")" in services


def test_services_section_hides_when_no_items():
    services = (ROOT / "frontend/components/specialist/SectionServices.tsx").read_text(encoding="utf-8")

    assert "if (!servicesBlock)" in services
    assert "if (!serviceRows.length)" in services
    assert "return null;" in services


def test_page_uses_section_services_component_with_blocks_payload():
    page = (ROOT / "frontend/pages/specialist_profile_page.tsx").read_text(encoding="utf-8")

    assert 'import SectionServices from "../components/specialist/SectionServices";' in page
    assert "<SectionServices blocks={payload?.blocks} />" in page


def test_bridge_runtime_renders_services_rows_without_inline_cta():
    bridge = (ROOT / "web_server.py").read_text(encoding="utf-8")

    assert "const renderServices = (blocks) =>" in bridge
    assert "listEl.className = 'specialist-list';" in bridge
    assert "specialist-list__item specialist-list__item--service" in bridge
    assert "specialist-service__price" in bridge
    assert "const buildServiceLabel = (item) => {" in bridge
    assert "return `${serviceName} — ${serviceDescription}`;" in bridge
    assert "if (!serviceLabel) {" in bridge
    assert "if (!listEl.children.length) {" in bridge
    assert "ctaWrap.className = 'service-cta';" not in bridge


def test_specialist_service_legacy_card_styles_removed():
    frontend_css = (ROOT / "frontend/styles/specialist.css").read_text(encoding="utf-8")
    bridge_css = (ROOT / "web/assets/specialist.css").read_text(encoding="utf-8")

    legacy_selectors = [
        ".services-grid",
        ".service-card",
        ".service-title",
        ".service-price",
        ".service-description",
        ".service-cta",
    ]

    for selector in legacy_selectors:
        assert selector not in frontend_css
        assert selector not in bridge_css

    assert ".specialist-list__item--service" in frontend_css
    assert ".specialist-service__price" in frontend_css
    assert ".specialist-list__item--service" in bridge_css
    assert ".specialist-service__price" in bridge_css
