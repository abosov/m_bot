from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "database/migrations/20260311_add_specialist_public_blocks.sql"


def test_specialist_public_blocks_migration_exists():
    assert MIGRATION_PATH.exists(), "specialist_public_block migration must exist"


def test_profile_cannot_have_duplicate_block_type():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "UNIQUE(profile_id, block_type)" in content
