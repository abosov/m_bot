CREATE TABLE specialist_public_block (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES specialist_public_profile(id) ON DELETE CASCADE,
    block_type TEXT NOT NULL,
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(profile_id, block_type)
);
