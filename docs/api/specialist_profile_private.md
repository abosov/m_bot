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
- `public_slug` is returned as `string | null` (if DB has `NULL`, API returns `null`).
- `is_published` is always returned as boolean.
- If draft profile does not exist, backend creates a minimal draft record.

### PUT `/api/specialist/profile`
Updates draft profile text fields.

Validation:
- `specialization`: `1..200` chars after trim (required)
- `hero_quote`: `0..200` chars after trim
- `about`, `education`, `services`, `reviews`: `0..8000` chars after trim
- derived `display_name` must be `<= 200`


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
- max size: `PROFILE_PHOTO_MAX_BYTES` (default 10MB)
- allowed content types: `image/jpeg`, `image/png`, `image/webp`
- replace logic: old `photo` media for profile is deleted and replaced by new one.

Response:
```json
{ "ok": true }
```

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
      "title": "Фото",
      "sort_order": 10,
      "created_at": "2026-03-10T10:00:00"
    }
  ]
}
```

Important:
- `file_key` is intentionally not returned.
- media files are private and must not be exposed via public API.

## Name fields source of truth
`first_name`, `middle_name`, `last_name` in `specialist_public_profile` are source of truth for private edit API.

`display_name` is derived on save for backward compatibility with public rendering:
- Save: `display_name = "first_name middle_name last_name"` (empty parts skipped, single spaces).
- Read fallback only: if all three name columns are `NULL`, API parses current `display_name` on-the-fly:
  - first token → `first_name`
  - last token → `last_name`
  - tokens between first/last → `middle_name`
  - if one token only: `first_name=token`, `last_name=""`, `middle_name=""`.
