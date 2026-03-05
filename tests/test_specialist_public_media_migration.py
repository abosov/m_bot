from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "database/migrations/20260312_add_specialist_public_media.sql"


def test_specialist_public_media_migration_exists():
    assert MIGRATION_PATH.exists(), "specialist_public_media migration must exist"


def test_media_type_is_limited_to_allowed_values():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'document'))" in content
