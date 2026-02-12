ALTER TABLE specialist
    ADD COLUMN IF NOT EXISTS master_onboarding_completed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS full_onboarding_completed_at TIMESTAMPTZ NULL;
