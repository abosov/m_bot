CREATE TABLE public_specialist_profile (
    id UUID PRIMARY KEY,
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
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_public_specialist_slug_format
        CHECK (public_slug ~ '^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$')
);

CREATE TABLE public_specialist_block (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public_specialist_profile(id) ON DELETE CASCADE,
    block_type TEXT NOT NULL,
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE public_specialist_review (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public_specialist_profile(id) ON DELETE CASCADE,
    author_name TEXT,
    rating INTEGER,
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_public_specialist_review_rating
        CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
);

CREATE TABLE public_specialist_media (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public_specialist_profile(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'document')),
    title TEXT,
    file_key TEXT,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_public_specialist_block_profile_sort
ON public_specialist_block(profile_id, sort_order);

CREATE INDEX idx_public_specialist_review_profile_sort
ON public_specialist_review(profile_id, sort_order);

CREATE INDEX idx_public_specialist_media_profile_sort
ON public_specialist_media(profile_id, sort_order);
