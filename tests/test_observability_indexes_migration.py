from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260306_add_observability_indexes.sql"


REQUIRED_SNIPPETS = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_specialist_id_created_at",
    "ON message_logs (specialist_id, created_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_bot_id_created_at",
    "ON message_logs (bot_id, created_at);",
    "ix_service_heartbeats_created_at",
    "ix_service_heartbeats_service_name_created_at",
    "column_name = 'created_at'",
    "column_name = 'ts'",
)


def test_observability_indexes_migration_exists_and_contains_required_indexes():
    assert MIGRATION_PATH.exists(), "observability indexes migration must exist"

    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for snippet in REQUIRED_SNIPPETS:
        assert snippet in content


def test_observability_indexes_migration_does_not_open_transaction_block():
    content_lower = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "begin;" not in content_lower
    assert "start transaction" not in content_lower
