from pathlib import Path
import re

from fastapi.testclient import TestClient

import web_server


REQUIRED_HEADER_ITEMS = (
    "Возможности",
    "Тарифы",
    "Для специалистов",
    "Контакты",
    "Подключить",
)

PUBLIC_ROUTES = (
    "/",
    "/features",
    "/pricing",
    "/specialists",
    "/contacts",
    "/privacy",
    "/terms",
    "/revoke-access",
    "/legal",
    "/privacy-ru",
    "/terms-ru",
    "/revoke-access-ru",
)


def _extract_header(html: str) -> str:
    match = re.search(r"<header class=\"site-header\">.*?</header>", html, re.S)
    assert match is not None, "Header is missing"
    return match.group(0)


def test_web_templates_use_single_header_placeholder() -> None:
    for html_file in sorted(Path("web").glob("*.html")):
        content = html_file.read_text(encoding="utf-8")
        assert content.count("{{SITE_HEADER}}") == 1, f"{html_file} should include exactly one SITE_HEADER placeholder"
        assert "<header class=\"site-header\">" not in content, f"{html_file} should not duplicate header markup"


def test_public_pages_render_unified_header_without_privacy_policy_link() -> None:
    client = TestClient(web_server.app)

    for route in PUBLIC_ROUTES:
        response = client.get(route)
        assert response.status_code == 200, f"Unexpected status on {route}: {response.status_code}"
        header_html = _extract_header(response.text)

        assert "Privacy Policy" not in header_html, f"Privacy Policy link still present in header on {route}"

        for marker in REQUIRED_HEADER_ITEMS:
            assert marker in header_html, f"Missing header item '{marker}' on {route}"
