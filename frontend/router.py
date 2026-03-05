import re

SPECIALIST_SLUG_RE = re.compile(r"^[A-Za-z]+[A-Za-z]_[1-9][0-9]$")
RESERVED_PATHS = {
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
}


def _normalize_path_segment(path_segment: str) -> str:
    return path_segment.strip().strip("/").lower()


def is_specialist_slug(path_segment: str) -> bool:
    normalized_segment = _normalize_path_segment(path_segment)

    if normalized_segment in RESERVED_PATHS:
        return False
    if not SPECIALIST_SLUG_RE.fullmatch(path_segment):
        return False

    suffix = int(path_segment.split("_", maxsplit=1)[1])
    return 10 <= suffix <= 30


def resolve_frontend_route(path: str) -> str:
    """Возвращает целевую страницу для frontend-роутинга.

    - `specialist_profile_page` для валидного `/{public_slug}`.
    - `site_default_router` для остальных путей.
    """
    normalized = path.strip("/")
    if "/" in normalized or not normalized:
        return "site_default_router"

    if is_specialist_slug(normalized):
        return "specialist_profile_page"

    return "site_default_router"
