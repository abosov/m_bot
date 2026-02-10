-- Migration: add specialist_calendar_settings table for onboarding calendar step.

CREATE TABLE IF NOT EXISTS specialist_calendar_settings (
    specialist_id UUID PRIMARY KEY REFERENCES specialist(specialist_id),
    calendar_id VARCHAR NOT NULL UNIQUE,
    calendar_summary VARCHAR NULL,
    calendar_time_zone VARCHAR NULL,
    source VARCHAR(32) NOT NULL,
    last_smoke_test_at TIMESTAMPTZ NULL,
    last_smoke_test_status VARCHAR(32) NULL,
    last_smoke_test_error VARCHAR(255) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_specialist_calendar_settings_calendar_id
ON specialist_calendar_settings (calendar_id);
