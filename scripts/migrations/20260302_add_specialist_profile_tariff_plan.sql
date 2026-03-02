DO $$
BEGIN
    CREATE TYPE tariffplan AS ENUM ('free', 'start', 'pro', 'team');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS tariff_plan tariffplan NOT NULL DEFAULT 'start';
