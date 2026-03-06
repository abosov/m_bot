# User Flow: Public Specialist Page

## Public URL
- Pattern: `/{public_slug}`
- Example: `/TsarevaE_12`

## Data source
Public page data is loaded from:
- `GET /api/public/specialists/{public_slug}`

## Visibility rule
Only records with `is_published=true` are visible publicly.
If profile is missing or not published, API returns `404 not_found`.

## Slug validation rules
`public_slug` must satisfy both:
1. Regex: `^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$`
2. Numeric suffix range: `10..30` inclusive

Slug lifecycle in private profile flow:
- slug is created during first successful save of block "Основное" in private profile editing;
- before that specialist profile stays in draft state without public link;
- after creation slug remains stable and is not regenerated on subsequent edits.

## Public page payload
Page consumes three sections:
- `profile` (name, specialization, quote, contacts, client bot username)
- `blocks` (text sections such as about/education/documents/services/reviews)
- `media` (metadata only)

## Security requirements
- Do not expose raw `file_key` to public clients.
- Do not expose internal `specialist` fields.
- Public media URLs are not implemented yet (`url=null` placeholder in API response).

## Future work
- Add backend media delivery endpoint with signed URLs / access validation.
- Extend docs with final media delivery contract after implementation.


## Dev seed: TsarevaE_12
For local visual verification you can seed a demo published profile (`TsarevaE_12`) in **dev only**.

```bash
APP_ENV=dev python -m backend.scripts.dev_seed_public_specialist
```

Seed includes:
- profile (`Евгения Царёва`, `Психолог, ЭФТ`, contacts, quote, `is_published=true`),
- blocks (`about`, `education`, `services`),
- two manual reviews,
- one media metadata record.

Security guard:
- script hard-stops unless `APP_ENV=dev`.
