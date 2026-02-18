CREATE TABLE IF NOT EXISTS web_auth_session (
    token_hash TEXT PRIMARY KEY,
    specialist_id UUID NOT NULL,
    tg_user_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_web_auth_session_specialist_id
ON web_auth_session (specialist_id);

CREATE INDEX IF NOT EXISTS ix_web_auth_session_expires_at
ON web_auth_session (expires_at);
