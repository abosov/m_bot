# Public Specialist API

## Purpose
Public JSON API for specialist public pages like `/TsarevaE_12`.

## Endpoint
`GET /api/public/specialists/{public_slug}`

## Data source of truth
Public read-side uses only these tables:
- `specialist_public_profile`
- `specialist_public_block`
- `specialist_public_media`

Notes:
- `is_published` is read from `specialist_public_profile` and unpublished profiles return `404`.
- Reviews are not implemented in `specialist_public_*` storage yet, so API currently returns `reviews: []` to keep response contract stable.

## Slug rules
- Format: `^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$`
- Suffix range: `10..30` (inclusive)

Invalid slug returns `400 Bad Request` with one of:
- `invalid_slug_format`
- `invalid_slug_suffix`
- `invalid_slug_suffix_range`

## Published-only behavior
- `200 OK`: published profile found.
- `404 Not Found`: profile does not exist or is not published.

## Response shape
```json
{
  "profile": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "public_slug": "TsarevaE_12",
    "display_name": "Евгения Царёва",
    "specialization": "Психолог, ЭФТ",
    "hero_quote": "Можно по-другому.",
    "contacts": {
      "telegram": "evgenia_tsareva",
      "whatsapp": "+79990000000",
      "phone": "+79991112233",
      "email": "info@example.com"
    },
    "client_bot_username": "zumbot_client_bot"
  },
  "blocks": [
    {
      "block_type": "about",
      "content": "О себе текст",
      "sort_order": 10,
      "updated_at": "2026-03-12T10:00:00"
    }
  ],
  "media": [
    {
      "media_type": "photo",
      "title": "Фото",
      "sort_order": 10,
      "url": null
    }
  ],
  "reviews": []
}
```

## Frontend contract notes
- Контакты читаются только из вложенного объекта `profile.contacts.{telegram,whatsapp,phone,email}`.
- Идентификатор специалиста для deep-link payload в client bot — `profile.id` (UUID).
  Пример payload: `book_<profile.id>` или `contact_specialist_<profile.id>`.
- Поля вида `profile.contact_telegram` / `profile.contact_whatsapp` / `profile.specialist_id` не являются частью контракта.

## Security notes
Public API MUST NOT return:
- raw media storage keys (`file_key`),
- OAuth tokens,
- internal specialist/private fields not in public schema.

`profile.profile_photo_url` returns public URL for specialist hero photo only; internal `file_key` is never returned.

Backend media delivery policy for this URL:
- only `media_type=photo` rows are publicly served;
- `media_type=document` keys are always rejected (`404 not_found`);
- old photo keys remain backward-compatible in delivery (no mass migration required).
