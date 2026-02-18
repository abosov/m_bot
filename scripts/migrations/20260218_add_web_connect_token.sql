CREATE TABLE IF NOT EXISTS web_connect_token (
    token_hash TEXT PRIMARY KEY,
    specialist_id UUID NOT NULL,
    tg_user_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_web_connect_token_specialist_id
ON web_connect_token (specialist_id);

CREATE INDEX IF NOT EXISTS ix_web_connect_token_expires_at
ON web_connect_token (expires_at);
