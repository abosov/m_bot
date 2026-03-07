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


def default_options(scroll_y):
    return {
        "scrollY": scroll_y,
        "viewportHeight": 800,
        "documentHeight": 3000,
        "stickyOffset": 100,
    }


def test_active_is_first_section_at_page_start():
    sections = [
        {"id": "about", "top": 120},
        {"id": "education", "top": 560},
        {"id": "documents", "top": 920},
    ]

    result = run_resolver(sections, default_options(scroll_y=0))

    assert result == "about"


def test_services_activates_right_after_probe_crosses_services_top():
    sections = [
        {"id": "about", "top": 100},
        {"id": "education", "top": 600},
        {"id": "documents", "top": 980},
        {"id": "services", "top": 1400},
        {"id": "reviews", "top": 1900},
    ]

    just_before = run_resolver(sections, default_options(scroll_y=1295))
    just_after = run_resolver(sections, default_options(scroll_y=1296))

    assert just_before == "documents"
    assert just_after == "services"


def test_reviews_activates_right_after_probe_crosses_reviews_top():
    sections = [
        {"id": "about", "top": 100},
        {"id": "education", "top": 600},
        {"id": "documents", "top": 980},
        {"id": "services", "top": 1400},
        {"id": "reviews", "top": 1900},
    ]

    just_before = run_resolver(sections, default_options(scroll_y=1795))
    just_after = run_resolver(sections, default_options(scroll_y=1796))

    assert just_before == "services"
    assert just_after == "reviews"


def test_long_previous_section_does_not_delay_switch_to_next_section():
    sections = [
        {"id": "about", "top": 100},
        {"id": "education", "top": 400},
        {"id": "documents", "top": 700},
        {"id": "services", "top": 2600},
        {"id": "reviews", "top": 2850},
    ]

    result = run_resolver(
        sections,
        {
            "scrollY": 2496,
            "viewportHeight": 800,
            "documentHeight": 5000,
            "stickyOffset": 100,
        },
    )

    assert result == "services"


def test_last_nav_section_is_active_close_to_page_bottom_with_booking_after_reviews():
    sections = [
        {"id": "about", "top": 100},
        {"id": "education", "top": 500},
        {"id": "documents", "top": 900},
        {"id": "services", "top": 1300},
        {"id": "reviews", "top": 1700},
    ]

    result = run_resolver(
        sections,
        {
            "scrollY": 2201,
            "viewportHeight": 800,
            "documentHeight": 3020,
            "stickyOffset": 100,
        },
    )

    assert result == "reviews"


def test_booking_cta_outside_nav_does_not_pull_active_back_from_reviews():
    sections = [
        {"id": "about", "top": 100},
        {"id": "education", "top": 500},
        {"id": "documents", "top": 900},
        {"id": "services", "top": 1300},
        {"id": "reviews", "top": 1700},
    ]

    result = run_resolver(
        sections,
        {
            "scrollY": 1900,
            "viewportHeight": 800,
            "documentHeight": 4200,
            "stickyOffset": 100,
        },
    )

    assert result == "reviews"
