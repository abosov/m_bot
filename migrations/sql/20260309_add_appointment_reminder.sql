-- Reminder idempotency ledger for scheduler/outbox reminder dispatch.

CREATE TABLE IF NOT EXISTS appointment_reminder (
    id UUID PRIMARY KEY,
    appointment_id UUID NOT NULL REFERENCES appointment(appointment_id) ON DELETE CASCADE,
    specialist_id UUID NOT NULL,
    reminder_type TEXT NOT NULL CHECK (reminder_type IN ('h24', 'h2')),
    due_at_utc TIMESTAMPTZ NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at_utc TIMESTAMPTZ NULL,
    UNIQUE (appointment_id, reminder_type)
);

CREATE INDEX IF NOT EXISTS ix_appointment_reminder_due_at_utc
    ON appointment_reminder (due_at_utc);

CREATE INDEX IF NOT EXISTS ix_appointment_reminder_sent_due
    ON appointment_reminder (sent_at_utc, due_at_utc);

CREATE INDEX IF NOT EXISTS ix_appointment_reminder_due_unsent
    ON appointment_reminder (due_at_utc)
    WHERE sent_at_utc IS NULL;
