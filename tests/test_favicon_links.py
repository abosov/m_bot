from fastapi.testclient import TestClient

import web_server


def test_every_html_template_has_global_favicon_links() -> None:
    required_markers = (
        "<!-- Global favicon -->",
        'href="/assets/icons/favicon.ico"',
        'href="/assets/icons/favicon-32.png"',
        'href="/assets/icons/favicon-16.png"',
    )
    for html_file in sorted(web_server.WEB_DIR.glob("*.html")):
        content = html_file.read_text(encoding="utf-8")
        for marker in required_markers:
            assert marker in content, f"{html_file} is missing {marker}"


def test_favicon_link_is_present_on_all_site_routes() -> None:
    client = TestClient(web_server.app)

    for route in sorted(web_server.SITE_PAGES):
        response = client.get(route)
        assert response.status_code == 200
        assert 'href="/assets/icons/favicon.ico"' in response.text


def test_assets_favicon_files_exist() -> None:
    icons_dir = web_server.ASSETS_DIR / "icons"
    assert (icons_dir / "favicon.ico").exists()
    assert (icons_dir / "favicon-32.png").exists()
    assert (icons_dir / "favicon-16.png").exists()
