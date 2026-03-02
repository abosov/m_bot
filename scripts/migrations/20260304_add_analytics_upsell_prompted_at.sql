ALTER TABLE specialist_profile
    ADD COLUMN IF NOT EXISTS analytics_upsell_prompted_at TIMESTAMPTZ NULL;
