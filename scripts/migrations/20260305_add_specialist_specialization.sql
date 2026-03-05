-- Add specialization field for specialist profile.
-- This is used for future filtering/catalog, collected during onboarding.
-- Must remain nullable for backward compatibility.

ALTER TABLE specialist
  ADD COLUMN specialization TEXT;

-- No defaults, no data migration.
