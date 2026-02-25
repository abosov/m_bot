-- Migration: add specialist_working_intervals table for up to 3 unified availability intervals.

CREATE TABLE IF NOT EXISTS specialist_working_intervals (
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id) ON DELETE CASCADE,
    idx SMALLINT NOT NULL,
    start_min SMALLINT NULL,
    end_min SMALLINT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_specialist_working_intervals_specialist_idx UNIQUE (specialist_id, idx),
    CONSTRAINT ck_specialist_working_intervals_idx CHECK (idx IN (1, 2, 3)),
    CONSTRAINT ck_specialist_working_intervals_start_min_range CHECK (start_min BETWEEN 0 AND 1439 OR start_min IS NULL),
    CONSTRAINT ck_specialist_working_intervals_end_min_range CHECK (end_min BETWEEN 1 AND 1440 OR end_min IS NULL),
    CONSTRAINT ck_specialist_working_intervals_pair_presence CHECK (
        (start_min IS NULL AND end_min IS NULL)
        OR (start_min IS NOT NULL AND end_min IS NOT NULL)
    ),
    CONSTRAINT ck_specialist_working_intervals_order CHECK (
        start_min IS NULL
        OR end_min IS NULL
        OR start_min < end_min
    )
);

CREATE INDEX IF NOT EXISTS ix_specialist_working_intervals_specialist_id
ON specialist_working_intervals (specialist_id);
