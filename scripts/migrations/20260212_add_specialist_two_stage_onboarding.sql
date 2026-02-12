ALTER TABLE specialist
    ADD COLUMN IF NOT EXISTS onboarding_master_completed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS onboarding_personal_completed_at TIMESTAMPTZ NULL;
