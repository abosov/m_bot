import re

from fastapi.testclient import TestClient

import web_server


RU_ROUTES = (
    "/",
    "/features",
    "/contacts",
    "/privacy-ru",
    "/terms-ru",
    "/legal",
    "/revoke-access-ru",
)

EN_ROUTES = (
    "/privacy",
    "/terms",
    "/revoke-access",
)

REQUIRED_MARKERS = (
    "Самозанятый: Босов Александр Михайлович",
    "ИНН: 772644000871",
)


def _extract_footer(html: str) -> str:
    match = re.search(r'<footer class="site-footer">.*?</footer>', html, re.S)
    assert match is not None, "Footer is missing"
    return match.group(0)


def test_web_templates_use_single_footer_placeholder() -> None:
    for html_file in sorted(web_server.WEB_DIR.glob("*.html")):
        content = html_file.read_text(encoding="utf-8")
        assert content.count("{{SITE_FOOTER}}") == 1, f"{html_file} should include exactly one SITE_FOOTER placeholder"
        assert '<footer class="site-footer">' not in content, f"{html_file} should not duplicate footer markup"


def test_site_footer_contains_only_current_legal_identity() -> None:
    client = TestClient(web_server.app)
    banned_markers = ("ООО «Зумбот Тех»", "7700000000")

    for route in (*RU_ROUTES, *EN_ROUTES):
        response = client.get(route)
        assert response.status_code == 200
        footer_html = _extract_footer(response.text)

        for marker in banned_markers:
            assert marker not in footer_html, f"{route} still contains banned marker: {marker}"

        for marker in REQUIRED_MARKERS:
            assert marker in footer_html, f"{route} misses required footer marker: {marker}"


def test_ru_footer_links_and_legal_block_are_consistent() -> None:
    client = TestClient(web_server.app)

    for route in RU_ROUTES:
        response = client.get(route)
        assert response.status_code == 200
        footer_html = _extract_footer(response.text)

        assert 'id="legal-info-footer"' in footer_html
        assert 'href="/privacy-ru"' in footer_html
        assert 'href="/terms-ru"' in footer_html
        assert 'href="/legal"' in footer_html
        assert 'href="/privacy"' not in footer_html
        assert 'href="/terms"' not in footer_html
        assert "https://zumbot.ru/" not in footer_html


def test_en_footer_links_and_legal_block_are_consistent() -> None:
    client = TestClient(web_server.app)

    for route in EN_ROUTES:
        response = client.get(route)
        assert response.status_code == 200
        footer_html = _extract_footer(response.text)

        assert 'id="legal-info-footer"' in footer_html
        assert 'href="/privacy"' in footer_html
        assert 'href="/terms"' in footer_html
        assert 'href="/legal"' in footer_html
        assert 'href="/privacy-ru"' not in footer_html
        assert 'href="/terms-ru"' not in footer_html
        assert "https://zumbot.ru/" not in footer_html
