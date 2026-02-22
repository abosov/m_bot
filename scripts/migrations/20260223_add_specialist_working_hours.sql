-- Migration: add specialist_working_hours table for normalized weekday working intervals.

CREATE TABLE IF NOT EXISTS specialist_working_hours (
    id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id) ON DELETE CASCADE,
    weekday INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_specialist_working_hours_weekday_range CHECK (weekday BETWEEN 0 AND 6),
    CONSTRAINT ck_specialist_working_hours_time_order CHECK (start_time < end_time)
);

CREATE INDEX IF NOT EXISTS ix_specialist_working_hours_specialist_weekday
ON specialist_working_hours (specialist_id, weekday);
