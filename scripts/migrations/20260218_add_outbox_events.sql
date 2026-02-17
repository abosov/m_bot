CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ NULL,
    error TEXT NULL,
    attempts INT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_outbox_events_processed_created_at
ON outbox_events (processed_at, created_at);
