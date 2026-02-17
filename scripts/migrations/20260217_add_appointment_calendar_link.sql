-- Migration: add appointment_calendar_link for stable appointment <-> Google event reverse sync mapping.

CREATE TABLE IF NOT EXISTS appointment_calendar_link (
    appointment_id UUID PRIMARY KEY REFERENCES appointment(appointment_id) ON DELETE CASCADE,
    specialist_id UUID NOT NULL,
    calendar_id TEXT NOT NULL,
    google_event_id TEXT NOT NULL,
    ical_uid TEXT NULL,
    event_etag TEXT NULL,
    event_updated TIMESTAMPTZ NULL,
    last_synced_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_appointment_calendar_link_event_calendar UNIQUE (google_event_id, calendar_id),
    CONSTRAINT uq_appointment_calendar_link_appointment_id UNIQUE (appointment_id)
);

CREATE INDEX IF NOT EXISTS ix_appointment_calendar_link_specialist_id
ON appointment_calendar_link (specialist_id);

CREATE INDEX IF NOT EXISTS ix_appointment_calendar_link_google_event_id
ON appointment_calendar_link (google_event_id);

CREATE INDEX IF NOT EXISTS ix_appointment_calendar_link_ical_uid
ON appointment_calendar_link (ical_uid);
