CREATE TABLE specialist_public_profile (
    id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id) ON DELETE CASCADE,
    public_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    hero_quote TEXT,
    contact_telegram TEXT,
    contact_whatsapp TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    client_bot_username TEXT NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_specialist_public_slug
ON specialist_public_profile(public_slug);
