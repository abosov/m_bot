ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS tariff_paid_until TIMESTAMPTZ NULL;

ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS tariff_period billingperiod NULL;

ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS tariff_last_paid_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS ix_specialist_profile_tariff_paid_until
    ON specialist_profile (tariff_paid_until);
