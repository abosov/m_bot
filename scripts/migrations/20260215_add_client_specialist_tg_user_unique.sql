-- Enforce unique client identity per specialist and Telegram user.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'uq_client_specialist_tg_user_id'
  ) THEN
    ALTER TABLE client
      ADD CONSTRAINT uq_client_specialist_tg_user_id
      UNIQUE (specialist_id, tg_user_id);
  END IF;
END
$$;
