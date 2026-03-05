from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260309_add_specialist_public_profile_name_parts.sql"


def test_name_parts_migration_exists():
    assert MIGRATION_PATH.exists(), "name parts migration must exist"


def test_name_parts_migration_contains_required_ddl_and_backfill():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "ALTER TABLE specialist_public_profile" in content
    assert "ADD COLUMN IF NOT EXISTS first_name TEXT" in content
    assert "ADD COLUMN IF NOT EXISTS middle_name TEXT" in content
    assert "ADD COLUMN IF NOT EXISTS last_name TEXT" in content
    assert "WHERE first_name IS NULL" in content
    assert "AND middle_name IS NULL" in content
    assert "AND last_name IS NULL" in content
    assert "display_name" in content
    assert "regexp_split_to_array" in content
