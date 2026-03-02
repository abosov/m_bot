ALTER TABLE specialist
    ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16),
    ADD COLUMN IF NOT EXISTS referrer_id UUID NULL,
    ADD COLUMN IF NOT EXISTS referral_bonus_awarded_at TIMESTAMPTZ NULL;

UPDATE specialist
SET referral_code = UPPER(SUBSTRING(REPLACE(specialist_id::text, '-', '') FROM 1 FOR 8))
WHERE referral_code IS NULL;

ALTER TABLE specialist
    ALTER COLUMN referral_code SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_specialist_referral_code'
    ) THEN
        ALTER TABLE specialist
            ADD CONSTRAINT uq_specialist_referral_code UNIQUE (referral_code);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_specialist_referrer_id'
    ) THEN
        ALTER TABLE specialist
            ADD CONSTRAINT fk_specialist_referrer_id
            FOREIGN KEY (referrer_id) REFERENCES specialist(specialist_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_specialist_referrer_id ON specialist(referrer_id);

ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS start_bonus_until TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS referral_bonus_months INTEGER NOT NULL DEFAULT 0;
