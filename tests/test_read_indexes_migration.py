from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260216_add_read_indexes.sql"


REQUIRED_STATEMENTS = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_specialist_id_start_at_utc",
    "ON appointment (specialist_id, start_at_utc);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_specialist_id_booking_state_start_at_utc",
    "ON appointment (specialist_id, booking_state, start_at_utc);",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_appointment_client_id_start_at_utc",
    "ON appointment (client_id, start_at_utc);",
)


def test_read_indexes_migration_exists_and_contains_required_indexes():
    assert MIGRATION_PATH.exists(), "read indexes migration must exist"

    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for statement in REQUIRED_STATEMENTS:
        assert statement in content


def test_read_indexes_migration_does_not_open_transaction_block():
    content_lower = MIGRATION_PATH.read_text(encoding="utf-8").lower()
    assert "begin;" not in content_lower
    assert "start transaction" not in content_lower
