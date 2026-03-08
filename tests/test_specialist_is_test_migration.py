from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260314_add_specialist_is_test.sql"


REQUIRED_STATEMENTS = (
    "ALTER TABLE specialist",
    "ADD COLUMN IF NOT EXISTS is_test BOOLEAN;",
    "UPDATE specialist",
    "SET is_test = FALSE",
    "WHERE is_test IS NULL;",
    "ALTER COLUMN is_test SET DEFAULT FALSE;",
    "ALTER COLUMN is_test SET NOT NULL;",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_specialist_is_test",
    "ON specialist (is_test);",
    "ADD CONSTRAINT specialist_test_system_exclusive",
    "CHECK (NOT (is_system AND is_test)) NOT VALID;",
    "VALIDATE CONSTRAINT specialist_test_system_exclusive;",
)


VERIFICATION_QUERIES = (
    "EXPLAIN SELECT COUNT(*) FROM specialist WHERE is_test = TRUE;",
    "SELECT COUNT(*) FROM specialist WHERE is_test IS NULL;",
    "SELECT COUNT(*) FROM specialist WHERE is_test = TRUE;",
    "SELECT COUNT(*) FROM specialist WHERE is_test = FALSE;",
)


def test_specialist_is_test_migration_exists_and_contains_required_steps():
    assert MIGRATION_PATH.exists(), "is_test migration must exist"

    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for statement in REQUIRED_STATEMENTS:
        assert statement in content


def test_specialist_is_test_migration_is_online_safe():
    content_lower = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "begin;" not in content_lower
    assert "start transaction" not in content_lower


def test_specialist_is_test_migration_contains_verification_queries():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for query in VERIFICATION_QUERIES:
        assert query in content
