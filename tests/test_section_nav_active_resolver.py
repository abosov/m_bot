import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOLVER_PATH = ROOT / "frontend/components/specialist/sectionNavActiveResolver.js"


def _run_resolver(sections: list[dict[str, int]], options: dict[str, int]) -> str | None:
    script = f"""
import {{ resolveActiveSectionId }} from 'file://{RESOLVER_PATH}';
const sections = {json.dumps(sections)};
const options = {json.dumps(options)};
const value = resolveActiveSectionId(sections, options);
console.log(value ?? 'null');
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = result.stdout.strip()
    return None if resolved == "null" else resolved


def test_resolver_activates_services_on_mobile_scroll_position():
    sections = [
        {"id": "about", "top": 320},
        {"id": "education", "top": 860},
        {"id": "documents", "top": 1220},
        {"id": "services", "top": 1480},
        {"id": "reviews", "top": 1800},
    ]

    active_id = _run_resolver(
        sections,
        {
            "scrollY": 1340,
            "viewportHeight": 812,
            "documentHeight": 2900,
            "stickyOffset": 146,
        },
    )

    assert active_id == "services"


def test_resolver_activates_reviews_on_desktop_and_keeps_it_near_bottom_with_booking_cta():
    sections = [
        {"id": "about", "top": 240},
        {"id": "education", "top": 900},
        {"id": "documents", "top": 1340},
        {"id": "services", "top": 1700},
        {"id": "reviews", "top": 1940},
    ]

    desktop_active = _run_resolver(
        sections,
        {
            "scrollY": 1810,
            "viewportHeight": 900,
            "documentHeight": 3400,
            "stickyOffset": 118,
        },
    )

    near_bottom_active = _run_resolver(
        sections,
        {
            "scrollY": 2580,
            "viewportHeight": 820,
            "documentHeight": 3420,
            "stickyOffset": 118,
        },
    )

    assert desktop_active == "reviews"
    assert near_bottom_active == "reviews"
