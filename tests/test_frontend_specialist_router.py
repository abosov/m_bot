from frontend.router import is_specialist_slug, resolve_frontend_route


def test_valid_slug_routes_to_specialist_profile_page():
    assert is_specialist_slug("TsarevaE_12") is True
    assert resolve_frontend_route("/TsarevaE_12") == "specialist_profile_page"


def test_invalid_slug_falls_back_to_default_router():
    assert is_specialist_slug("bad-slug") is False
    assert resolve_frontend_route("/bad-slug") == "site_default_router"


def test_reserved_paths_fall_back_to_default_router():
    reserved_paths = (
        "pricing",
        "privacy",
        "terms",
        "revoke-access",
        "api",
        "static",
        "assets",
        "robots.txt",
        "sitemap.xml",
        "favicon.ico",
        "healthz",
        "readyz",
        "docs",
        "blog",
        "specialists",
        "admin",
    )

    for path in reserved_paths:
        assert is_specialist_slug(path) is False
        assert is_specialist_slug(path.upper()) is False
        assert is_specialist_slug(f"/{path}/") is False
        assert resolve_frontend_route(f"/{path}") == "site_default_router"


def test_reserved_paths_with_case_and_slashes_do_not_resolve_to_specialist_page():
    for path in ("/Pricing", "/READYZ", "/docs/", "/AdMiN"):
        assert resolve_frontend_route(path) == "site_default_router"
