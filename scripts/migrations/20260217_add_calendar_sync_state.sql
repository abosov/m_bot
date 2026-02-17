-- Migration: add calendar_sync_state for Google Calendar reverse-sync cursor and watch-channel metadata.

CREATE TABLE IF NOT EXISTS calendar_sync_state (
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id),
    calendar_id TEXT NOT NULL,
    sync_token TEXT NULL,
    channel_id TEXT NULL,
    resource_id TEXT NULL,
    channel_expiration TIMESTAMPTZ NULL,
    last_success_at TIMESTAMPTZ NULL,
    last_error_at TIMESTAMPTZ NULL,
    error_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (specialist_id, calendar_id)
);
