from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_FIELDS = ("master_onboarding_completed_at", "full_onboarding_completed_at")
ALLOWED_PATHS = {
    "scripts/migrations/20260212_add_specialist_onboarding_phase_timestamps.sql",
    "tests/test_onboarding_field_naming.py",
}


def test_legacy_onboarding_field_names_only_exist_in_compat_migration():
    offenders = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if "/.git/" in f"/{rel}/":
            continue
        if rel in ALLOWED_PATHS:
            continue
        if path.suffix not in {".py", ".sql", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(field in text for field in LEGACY_FIELDS):
            offenders.append(rel)

    assert offenders == []
