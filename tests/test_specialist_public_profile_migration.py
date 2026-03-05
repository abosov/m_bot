from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "database/migrations/20260310_add_specialist_public_profile.sql"


def test_specialist_public_profile_migration_exists():
    assert MIGRATION_PATH.exists(), "specialist_public_profile migration must exist"


def test_public_slug_is_required_and_unique():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "public_slug TEXT NOT NULL UNIQUE" in content
    assert "CREATE UNIQUE INDEX idx_specialist_public_slug" in content
    assert "ON specialist_public_profile(public_slug);" in content
