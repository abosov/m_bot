CREATE TABLE IF NOT EXISTS notification_log (
    id UUID PRIMARY KEY,
    outbox_event_id UUID NOT NULL REFERENCES outbox_events(id) ON DELETE CASCADE,
    target TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_notification_log_outbox_event_target UNIQUE (outbox_event_id, target)
);

CREATE INDEX IF NOT EXISTS ix_notification_log_outbox_event_id
ON notification_log (outbox_event_id);
