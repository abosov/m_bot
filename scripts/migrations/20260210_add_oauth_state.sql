-- Migration: add oauth_state table used for one-time Google OAuth callback validation.
-- Postgres-friendly: creates enum only if missing.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'oauthstatetype') THEN
        CREATE TYPE oauthstatetype AS ENUM ('google_connect', 'google_reconnect');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS oauth_state (
    oauth_state_id UUID PRIMARY KEY,
    state VARCHAR NOT NULL UNIQUE,
    type oauthstatetype NOT NULL,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_oauth_state_expires_at
ON oauth_state (expires_at);
