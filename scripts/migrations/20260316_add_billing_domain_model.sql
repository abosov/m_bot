DO $$
BEGIN
    CREATE TYPE billingprovider AS ENUM ('yookassa');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE billingsubscriptionstatus AS ENUM (
        'inactive',
        'pending_payment',
        'active',
        'grace',
        'expired',
        'canceled'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE billingpaymentstatus AS ENUM (
        'new',
        'pending',
        'waiting_for_capture',
        'succeeded',
        'canceled',
        'refunded',
        'error'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE billingwebhookprocessedstatus AS ENUM (
        'received',
        'ignored',
        'processed',
        'failed'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS billing_tariffs (
    tariff_id UUID PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    price_minor INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    period_days INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
    subscription_id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL UNIQUE REFERENCES specialist(specialist_id),
    tariff_id UUID NOT NULL REFERENCES billing_tariffs(tariff_id),
    status billingsubscriptionstatus NOT NULL,
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    grace_until TIMESTAMPTZ NULL,
    last_payment_id UUID NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billing_payments (
    payment_id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id),
    subscription_id UUID NULL REFERENCES billing_subscriptions(subscription_id),
    tariff_id UUID NOT NULL REFERENCES billing_tariffs(tariff_id),
    provider billingprovider NOT NULL,
    provider_payment_id TEXT NULL,
    provider_idempotence_key TEXT NOT NULL UNIQUE,
    amount_minor INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status billingpaymentstatus NOT NULL,
    confirmation_url TEXT NULL,
    return_url TEXT NULL,
    description TEXT NULL,
    metadata_json JSONB NULL,
    paid_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_billing_subscriptions_last_payment_id'
    ) THEN
        ALTER TABLE billing_subscriptions
            ADD CONSTRAINT fk_billing_subscriptions_last_payment_id
            FOREIGN KEY (last_payment_id) REFERENCES billing_payments(payment_id);
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS billing_webhook_events (
    event_id UUID PRIMARY KEY,
    provider billingprovider NOT NULL,
    event_type TEXT NOT NULL,
    provider_event_id TEXT NULL,
    dedupe_hash TEXT NOT NULL,
    provider_payment_id TEXT NULL,
    payload_json JSONB NOT NULL,
    source_ip TEXT NULL,
    processing_status billingwebhookprocessedstatus NOT NULL,
    processing_error TEXT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS billing_access_log (
    log_id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id),
    subscription_id UUID NULL REFERENCES billing_subscriptions(subscription_id),
    reason TEXT NOT NULL,
    old_status billingsubscriptionstatus NULL,
    new_status billingsubscriptionstatus NOT NULL,
    details_json JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_billing_payments_provider_payment_id
    ON billing_payments (provider_payment_id);

CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_status
    ON billing_subscriptions (status);

CREATE INDEX IF NOT EXISTS ix_billing_subscriptions_current_period_end
    ON billing_subscriptions (current_period_end);

CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_webhook_events_provider_event_id
    ON billing_webhook_events (provider, provider_event_id)
    WHERE provider_event_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_webhook_events_provider_dedupe_hash
    ON billing_webhook_events (provider, dedupe_hash);

CREATE INDEX IF NOT EXISTS ix_billing_webhook_events_provider_payment_id
    ON billing_webhook_events (provider, provider_payment_id);

CREATE INDEX IF NOT EXISTS ix_billing_webhook_events_processing_status_received_at
    ON billing_webhook_events (processing_status, received_at);
