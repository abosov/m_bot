from pathlib import Path


def test_site_footer_contains_only_current_legal_identity() -> None:
    web_dir = Path("web")
    banned_markers = ("ООО «Зумбот Тех»", "7700000000")
    required_markers = (
        "Самозанятый: Босов Александр Михайлович",
        "ИНН: 772644000871",
    )

    for html_file in sorted(web_dir.glob("*.html")):
        content = html_file.read_text(encoding="utf-8")
        if "site-footer" not in content:
            continue

        for marker in banned_markers:
            assert marker not in content, f"{html_file} still contains banned marker: {marker}"

        for marker in required_markers:
            assert marker in content, f"{html_file} misses required footer marker: {marker}"
