from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260212_add_admin_read_indexes.sql"


REQUIRED_STATEMENTS = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_created_at",
    "ON message_logs (created_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_tg_user_id_created_at",
    "ON message_logs (tg_user_id, created_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_message_logs_is_error_created_at",
    "ON message_logs (is_error, created_at);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_heartbeats_ts",
    "ON service_heartbeats (ts);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_heartbeats_service_name_ts",
    "ON service_heartbeats (service_name, ts);",
)


def test_admin_indexes_migration_exists_and_contains_required_indexes():
    assert MIGRATION_PATH.exists(), "admin indexes migration must exist"

    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for statement in REQUIRED_STATEMENTS:
        assert statement in content


def test_admin_indexes_migration_does_not_open_transaction_block():
    content_lower = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "begin;" not in content_lower
    assert "start transaction" not in content_lower
