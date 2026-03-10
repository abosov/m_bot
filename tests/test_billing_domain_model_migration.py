from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "scripts/migrations/20260316_add_billing_domain_model.sql"


REQUIRED_SNIPPETS = (
    "CREATE TABLE IF NOT EXISTS billing_tariffs",
    "CREATE TABLE IF NOT EXISTS billing_subscriptions",
    "CREATE TABLE IF NOT EXISTS billing_payments",
    "CREATE TABLE IF NOT EXISTS billing_webhook_events",
    "CREATE TABLE IF NOT EXISTS billing_access_log",
    "code TEXT NOT NULL UNIQUE",
    "provider_idempotence_key TEXT NOT NULL UNIQUE",
    "ix_billing_payments_provider_payment_id",
    "ix_billing_subscriptions_status",
    "ix_billing_subscriptions_current_period_end",
    "provider_event_id TEXT NULL",
    "dedupe_hash TEXT NOT NULL",
    "provider_payment_id TEXT NULL",
    "processing_status billingwebhookprocessedstatus NOT NULL",
    "received_at TIMESTAMPTZ NOT NULL DEFAULT now()",
    "uq_billing_webhook_events_provider_event_id",
    "WHERE provider_event_id IS NOT NULL;",
    "uq_billing_webhook_events_provider_dedupe_hash",
    "ON billing_webhook_events (provider, dedupe_hash);",
    "ix_billing_webhook_events_provider_payment_id",
    "ix_billing_webhook_events_processing_status_received_at",
)


def test_billing_domain_model_migration_exists_and_contains_required_schema():
    assert MIGRATION_PATH.exists(), "billing domain migration must exist"

    content = MIGRATION_PATH.read_text(encoding="utf-8")

    for snippet in REQUIRED_SNIPPETS:
        assert snippet in content


def test_billing_domain_model_migration_declares_required_enums():
    content = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "CREATE TYPE billingprovider AS ENUM ('yookassa');" in content
    assert "CREATE TYPE billingsubscriptionstatus AS ENUM" in content
    assert "CREATE TYPE billingpaymentstatus AS ENUM" in content
    assert "CREATE TYPE billingwebhookprocessedstatus AS ENUM" in content
