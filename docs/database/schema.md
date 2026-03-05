# Database schema (selected tables)

## specialist
- specialist_id (uuid, pk)
- public_name (text, nullable)
- specialization (text, nullable)
- telegram_bot_token (text, nullable)
- calendar_id (text, nullable)
- status (enum, not null)

## public_specialist_profile
- id (uuid, pk)
- public_slug (text, unique, not null)
- display_name (text, not null)
- specialization (text, not null; snapshot for public page content)
- hero_quote (text, nullable)
- contact_telegram/contact_whatsapp/contact_phone/contact_email (text, nullable)
- client_bot_username (text, not null)
- is_published (boolean, not null, default false)
- created_at, updated_at (timestamp, not null)

## public_specialist_block
- id (uuid, pk)
- profile_id (uuid, fk -> public_specialist_profile.id, on delete cascade)
- block_type (text, not null)
- content (text, not null)
- sort_order (integer, not null)
- updated_at (timestamp, not null)

## public_specialist_review
- id (uuid, pk)
- profile_id (uuid, fk -> public_specialist_profile.id, on delete cascade)
- author_name (text, nullable)
- rating (integer, nullable, 1..5)
- content (text, not null)
- sort_order (integer, not null)
- created_at (timestamp, not null)

## public_specialist_media
- id (uuid, pk)
- profile_id (uuid, fk -> public_specialist_profile.id, on delete cascade)
- media_type (text, not null; `photo|document`)
- title (text, nullable)
- file_key (text, nullable; private storage key, not for public API responses)
- sort_order (integer, not null)
- created_at (timestamp, not null)

## Notes
- `specialist.specialization` is nullable and added via SQL migration `scripts/migrations/20260305_add_specialist_specialization.sql`.
- ORM mirrors this as a nullable text field in `database.py`.
- Public page specialization is intentionally stored as a snapshot in `public_specialist_profile.specialization` to keep published content stable independently from internal specialist profile edits.
- Storage metadata `public_specialist_media.file_key` is private and MUST NOT be returned by public API.
