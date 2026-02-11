ALTER TABLE specialist_profile
  ADD COLUMN IF NOT EXISTS slot_step_min INTEGER NOT NULL DEFAULT 15;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_specialist_profile_slot_step_min'
  ) THEN
    ALTER TABLE specialist_profile
      ADD CONSTRAINT ck_specialist_profile_slot_step_min
      CHECK (slot_step_min IN (60,30,15,10));
  END IF;
END
$$;
