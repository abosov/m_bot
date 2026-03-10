# Private API: specialist profile draft

## Auth
- Cookie-based auth only via existing `web_auth_session` cookie.
- Cookie is obtained through existing web-connect flow (`POST /auth/telegram/consume`).

## Endpoints

### GET `/api/specialist/profile`
Returns current draft values for specialist profile edit form.

Response DTO:
```json
{
  "first_name": "",
  "middle_name": "",
  "last_name": "",
  "specialization": "",
  "hero_quote": "",
  "about": "",
  "education": "",
  "services": "",
  "reviews": "",
  "public_slug": null,
  "is_published": false
}
```

Notes:
- Returns only form fields; no internal fields (`file_key`, media raw storage keys, IDs of profile internals).
- Empty text values are returned as empty strings (`""`) consistently.
- `public_slug` is returned as `string | null`. Before first successful save of block "Основное" slug may be `null`; after first successful save, slug is generated and returned immediately.
- `is_published` is always returned as boolean.
- If draft profile does not exist, backend creates a minimal draft record.

### PUT `/api/specialist/profile`
Updates draft profile text fields.

UI usage note:
- block "Основное" sends only `first_name`, `middle_name`, `last_name`, `specialization`;
- `hero_quote` is edited in a separate "Цитата" block after `public_slug` appears.

Validation:
- `specialization`: `1..200` chars after trim (required)
- `hero_quote`: `0..200` chars after trim
- `about`, `education`, `services`, `reviews`: `0..8000` chars after trim
- derived `display_name` must be `<= 200`

Slug generation rules on first successful save of "Основное":
- if `public_slug` is empty/`NULL`, backend generates slug and persists to `specialist_public_profile.public_slug`.
- source for slug base: `first_name + last_name`; fallback: `display_name`.
- normalization: predictable transliteration to latin (`а->a`, `б->b`, `в->v`, ..., `я->ya`), lowercase, remove spaces/special chars, enforce leading letter.
- resulting format: `^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$`, suffix range `10..30`.
- collision handling: pick next free suffix in range.
- if all suffixes occupied, API returns `409 slug_generation_failed`.
- slug is stable: after first creation it is not regenerated on subsequent edits.


### POST `/api/specialist/profile/publish`
Publishes specialist public profile (`is_published=true`).

Rules:
- specialist id is taken only from verified `web_auth_session` cookie.
- profile can be published only when `public_slug` is set.

Response:
```json
{ "ok": true, "is_published": true }
```

Errors:
- `401 unauthorized` — missing/invalid web session.
- `422 slug_missing` — profile slug is empty or missing.

### POST `/api/specialist/profile/unpublish`
Unpublishes specialist public profile (`is_published=false`).

Response:
```json
{ "ok": true, "is_published": false }
```

Errors:
- `401 unauthorized` — missing/invalid web session.

## Media upload endpoints

### POST `/api/specialist/profile/photo`
Multipart upload for profile photo (`file`).

Rules:
- max size: `PROFILE_PHOTO_MAX_BYTES` (default 10MB), overflow -> `413 file_too_large`
- input types: `image/jpeg`, `image/png`, `image/webp` (validated by magic bytes + decode)
- backend pipeline: EXIF normalize -> center crop 4:5 -> resize 800x1000 -> JPEG quality=85
- storage key: `media/specialists/{specialist_id}/profile_photo.jpg`
- replace logic: previous profile photo file is removed and replaced by normalized JPEG.
- transaction-safe write flow: upload is staged to temp file first, DB commit is executed, then file is atomically promoted to final hero key.

Response:
```json
{ "ok": true }
```


### DELETE `/api/specialist/profile/photo`
Deletes current specialist profile photo(s).

Rules:
- removes only `media_type=photo` rows for current specialist profile
- does not touch `media_type=document` rows
- endpoint is idempotent: if no photo exists, returns success
- after DB commit backend removes corresponding file(s) from storage

Response:
```json
{ "ok": true }
```

Errors:
- `401 unauthorized` — missing/invalid web session.

### POST `/api/specialist/profile/documents`
Multipart upload for document (`file`) with optional `title` form field.

Rules:
- max size: `PROFILE_DOCUMENT_MAX_BYTES` (default 20MB)
- allowed content types: `application/pdf`, `image/jpeg`, `image/png`
- documents are appended with `media_type=document`
- if `title` is empty, sanitized original filename is used.

Response:
```json
{ "ok": true }
```

### GET `/api/specialist/profile/media`
Returns media metadata for form UI.

Response example:
```json
{
  "items": [
    {
      "id": "uuid",
      "media_type": "photo",
      "file_key": "media/specialists/<specialist_id>/profile_photo.jpg",
      "title": "Фото",
      "sort_order": 10,
      "created_at": "2026-03-10T10:00:00"
    }
  ]
}
```

Important:
- `file_key` is returned only for `media_type=photo` to support current thumbnail rendering in private editor.
- For `media_type=document`, `file_key` is always `null` (raw document storage keys are not exposed).
- Media files remain private and must not be exposed via public specialist API.

## Name fields source of truth
`first_name`, `middle_name`, `last_name` in `specialist_public_profile` are source of truth for private edit API.

`display_name` is derived on save for backward compatibility with public rendering:
- Save: `display_name = "first_name middle_name last_name"` (empty parts skipped, single spaces).
- Read fallback only: if all three name columns are `NULL`, API parses current `display_name` on-the-fly:
  - first token → `first_name`
  - last token → `last_name`
  - tokens between first/last → `middle_name`
  - if one token only: `first_name=token`, `last_name=""`, `middle_name=""`.
