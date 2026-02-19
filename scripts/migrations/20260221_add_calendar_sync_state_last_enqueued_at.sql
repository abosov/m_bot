ALTER TABLE calendar_sync_state
ADD COLUMN IF NOT EXISTS last_enqueued_at TIMESTAMPTZ NULL;
