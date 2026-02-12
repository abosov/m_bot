ALTER TABLE specialist
    ADD COLUMN IF NOT EXISTS onboarding_master_completed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS onboarding_personal_completed_at TIMESTAMPTZ NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'specialist' AND column_name = 'master_onboarding_completed_at'
    ) THEN
        EXECUTE 'UPDATE specialist
                 SET onboarding_master_completed_at = COALESCE(onboarding_master_completed_at, master_onboarding_completed_at)
                 WHERE master_onboarding_completed_at IS NOT NULL';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'specialist' AND column_name = 'full_onboarding_completed_at'
    ) THEN
        EXECUTE 'UPDATE specialist
                 SET onboarding_personal_completed_at = COALESCE(onboarding_personal_completed_at, full_onboarding_completed_at)
                 WHERE full_onboarding_completed_at IS NOT NULL';
    END IF;
END $$;
