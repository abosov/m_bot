ALTER TABLE specialist_profile
  DROP CONSTRAINT IF EXISTS ck_specialist_profile_slot_step_min;

ALTER TABLE specialist_profile
  ADD CONSTRAINT ck_specialist_profile_slot_step_min
  CHECK (
    slot_step_min >= 5
    AND slot_step_min <= session_duration_min
    AND MOD(slot_step_min, 5) = 0
  );
