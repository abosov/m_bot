from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "database/migrations/20260313_add_public_specialist_storage.sql"


def test_public_specialist_storage_migration_exists():
    assert MIGRATION_PATH.exists(), "public specialist storage migration must exist"


def test_public_specialist_storage_migration_contains_required_tables_and_constraints():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE public_specialist_profile" in content
    assert "public_slug TEXT NOT NULL UNIQUE" in content
    assert "CHECK (public_slug ~ '^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$')" in content

    assert "CREATE TABLE public_specialist_block" in content
    assert "REFERENCES public_specialist_profile(id) ON DELETE CASCADE" in content

    assert "CREATE TABLE public_specialist_review" in content
    assert "rating INTEGER" in content
    assert "CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)" in content

    assert "CREATE TABLE public_specialist_media" in content
    assert "media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'document'))" in content
    assert "file_key TEXT" in content
