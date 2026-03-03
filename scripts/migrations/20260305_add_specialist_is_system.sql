ALTER TABLE specialist
ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE specialist
SET is_system = TRUE
WHERE specialist_id IN (
  SELECT specialist_id FROM specialist_auth_telegram WHERE tg_username = 'zumhelper_bot'
);
