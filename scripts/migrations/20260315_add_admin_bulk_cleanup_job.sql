-- US-AD-12: async bulk cleanup admin job tracking table.
-- Tracks lifecycle and progress for bulk test-account cleanup execution.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS admin_bulk_cleanup_job (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL,
    total_specialists INTEGER NOT NULL DEFAULT 0,
    processed_specialists INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT admin_bulk_cleanup_job_status_chk
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
    CONSTRAINT admin_bulk_cleanup_job_total_specialists_nonnegative_chk
        CHECK (total_specialists >= 0),
    CONSTRAINT admin_bulk_cleanup_job_processed_specialists_nonnegative_chk
        CHECK (processed_specialists >= 0),
    CONSTRAINT admin_bulk_cleanup_job_error_count_nonnegative_chk
        CHECK (error_count >= 0),
    CONSTRAINT admin_bulk_cleanup_job_processed_lte_total_chk
        CHECK (processed_specialists <= total_specialists)
);

CREATE INDEX IF NOT EXISTS ix_admin_bulk_cleanup_job_status
    ON admin_bulk_cleanup_job (status);

CREATE INDEX IF NOT EXISTS ix_admin_bulk_cleanup_job_created_at
    ON admin_bulk_cleanup_job (created_at);
