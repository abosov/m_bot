import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOLVER_PATH = (ROOT / "frontend/components/specialist/sectionNavActiveResolver.js").as_uri()


def run_resolver(sections, options):
    script = f"""
import {{ resolveActiveSectionId }} from {json.dumps(RESOLVER_PATH)};
const sections = {json.dumps(sections)};
const options = {json.dumps(options)};
const result = resolveActiveSectionId(sections, options);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def default_options(scroll_y, *, sticky_offset=100, viewport_height=800, document_height=4200):
    return {
        "scrollY": scroll_y,
        "viewportHeight": viewport_height,
        "documentHeight": document_height,
        "stickyOffset": sticky_offset,
    }


def test_services_activates_with_mobile_like_sticky_offset():
    sections = [
        {"id": "about", "top": 120, "bottom": 780, "height": 660},
        {"id": "education", "top": 780, "bottom": 1560, "height": 780},
        {"id": "documents", "top": 1560, "bottom": 2340, "height": 780},
        {"id": "services", "top": 2340, "bottom": 3320, "height": 980},
        {"id": "reviews", "top": 3320, "bottom": 3560, "height": 240},
    ]

    result = run_resolver(sections, default_options(scroll_y=2140, sticky_offset=190, document_height=5200))

    assert result == "services"


def test_reviews_activates_as_last_nav_section_before_booking_cta():
    sections = [
        {"id": "about", "top": 100, "bottom": 580, "height": 480},
        {"id": "education", "top": 580, "bottom": 1100, "height": 520},
        {"id": "documents", "top": 1100, "bottom": 1580, "height": 480},
        {"id": "services", "top": 1580, "bottom": 2100, "height": 520},
        {"id": "reviews", "top": 2100, "bottom": 2320, "height": 220},
    ]

    result = run_resolver(sections, default_options(scroll_y=1880, document_height=4200))

    assert result == "reviews"


def test_short_last_section_can_still_become_active_by_visible_overlap():
    sections = [
        {"id": "about", "top": 120, "bottom": 860, "height": 740},
        {"id": "education", "top": 860, "bottom": 1620, "height": 760},
        {"id": "documents", "top": 1620, "bottom": 2500, "height": 880},
        {"id": "services", "top": 2500, "bottom": 3460, "height": 960},
        {"id": "reviews", "top": 3460, "bottom": 3540, "height": 80},
    ]

    result = run_resolver(sections, default_options(scroll_y=3060, sticky_offset=120, viewport_height=760, document_height=5000))

    assert result == "reviews"


def test_high_sticky_offset_does_not_break_transition_to_services():
    sections = [
        {"id": "about", "top": 120, "bottom": 880, "height": 760},
        {"id": "education", "top": 880, "bottom": 1720, "height": 840},
        {"id": "documents", "top": 1720, "bottom": 2440, "height": 720},
        {"id": "services", "top": 2440, "bottom": 3200, "height": 760},
        {"id": "reviews", "top": 3200, "bottom": 3500, "height": 300},
    ]

    result = run_resolver(sections, default_options(scroll_y=2200, sticky_offset=260, viewport_height=780, document_height=4600))

    assert result == "services"


def test_near_bottom_prefers_reviews_not_services():
    sections = [
        {"id": "about", "top": 100, "bottom": 700, "height": 600},
        {"id": "education", "top": 700, "bottom": 1300, "height": 600},
        {"id": "documents", "top": 1300, "bottom": 1900, "height": 600},
        {"id": "services", "top": 1900, "bottom": 2600, "height": 700},
        {"id": "reviews", "top": 2600, "bottom": 2760, "height": 160},
    ]

    result = run_resolver(sections, default_options(scroll_y=3410, sticky_offset=120, viewport_height=760, document_height=4180))

    assert result == "reviews"


def test_short_reviews_section_with_missing_bottom_is_resolved_using_neighbors():
    sections = [
        {"id": "about", "top": 120},
        {"id": "education", "top": 760},
        {"id": "documents", "top": 1320},
        {"id": "services", "top": 2020},
        {"id": "reviews", "top": 2700, "height": 40},
    ]

    result = run_resolver(sections, default_options(scroll_y=2380, sticky_offset=160, viewport_height=760, document_height=4100))

    assert result == "reviews"
