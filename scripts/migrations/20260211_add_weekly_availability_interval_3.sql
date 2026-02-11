-- Add third daily interval for specialist weekly availability.
ALTER TABLE weekly_availability
    ADD COLUMN IF NOT EXISTS interval_3_start TIME NULL,
    ADD COLUMN IF NOT EXISTS interval_3_end TIME NULL;
