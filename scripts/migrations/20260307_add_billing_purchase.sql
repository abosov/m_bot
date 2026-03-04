DO $$
BEGIN
    CREATE TYPE billingperiod AS ENUM ('monthly', 'yearly');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE billingpurchasestatus AS ENUM (
        'pending',
        'awaiting_payment',
        'succeeded',
        'canceled',
        'expired',
        'error'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS billing_purchase (
    purchase_id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id),
    tg_user_id BIGINT NOT NULL,
    plan tariffplan NOT NULL,
    period billingperiod NOT NULL,
    amount_rub_int INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB',
    status billingpurchasestatus NOT NULL,
    pay_token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    yookassa_payment_id TEXT NULL UNIQUE,
    yookassa_status TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_billing_purchase_specialist_id
    ON billing_purchase (specialist_id);

CREATE INDEX IF NOT EXISTS ix_billing_purchase_expires_at
    ON billing_purchase (expires_at);

CREATE INDEX IF NOT EXISTS ix_billing_purchase_status_created_at
    ON billing_purchase (status, created_at);
