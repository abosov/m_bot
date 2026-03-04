-- Immutable audit log for admin actions (US-AD-7).
-- Requires pgcrypto for gen_random_uuid().

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id TEXT NULL,
    admin_subject TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id UUID NOT NULL,
    success BOOLEAN NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT NULL,
    error_message TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_admin_audit_log_created_at_desc
    ON admin_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_admin_audit_log_target_type_target_id_created_at_desc
    ON admin_audit_log (target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_admin_audit_log_action_created_at_desc
    ON admin_audit_log (action, created_at DESC);
