CREATE TABLE specialist_public_media (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES specialist_public_profile(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'document')),
    file_key TEXT NOT NULL,
    title TEXT,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
