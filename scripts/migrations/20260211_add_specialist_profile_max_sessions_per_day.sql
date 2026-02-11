ALTER TABLE specialist_profile
  ADD COLUMN IF NOT EXISTS max_sessions_per_day INTEGER NOT NULL DEFAULT 4;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_specialist_profile_max_sessions_per_day'
  ) THEN
    ALTER TABLE specialist_profile
      ADD CONSTRAINT ck_specialist_profile_max_sessions_per_day
      CHECK (max_sessions_per_day >= 1 AND max_sessions_per_day <= 20);
  END IF;
END
$$;
