# User Flow: Public Specialist Page

## Public URL
- Pattern: `/{public_slug}`
- Example: `/TsarevaE_12`

## Data source
Public page data is loaded from:
- `GET /api/public/specialists/{public_slug}`
- Runtime bridge for `GET /{public_slug}` builds absolute API URL from backend config: `${BASE_URL}/api/public/specialists/{public_slug}`.

## Website routing
- Реальный route на сайте: `GET /{public_slug}`.
- Route проходит через `frontend.router.resolve_frontend_route(path)`.
- Если route resolved как `specialist_profile_page`, сайт рендерит полноценный HTML-мост публичной страницы специалиста (sticky header + hero + контентные секции + CTA) и frontend-логика запрашивает `GET /api/public/specialists/{public_slug}`.
- Source of truth for this bridge: `web_server.py` route `@app.get("/{public_slug}")` (single full-page HTML bridge, legacy ветки отсутствуют).
- Legacy minimal-шаблон (только name/specialization/quote) больше не используется.
- Legacy DOM IDs `specialist-loading`, `specialist-not-found`, `specialist-content` в runtime-странице отсутствуют; используются `public-specialist-loading`, `public-specialist-not-found`, `specialist-page`.
- Если slug валиден, но профиль не найден/не опубликован, страница показывает site-level not found state.
- Невалидные slug и non-slug пути не перехватываются и обрабатываются обычным routing сайта.


## Public page visual order
1. Имя / отчество / фамилия (в `display_name`)
2. Специализация
3. Sticky-меню
4. Hero: фото слева, цитата справа
5. О себе
6. Образование
7. Документы
8. Услуги и цены
9. Отзывы

Если фото отсутствует, левая колонка hero сохраняется без поломки layout.
Если цитата пустая, правая колонка с цитатой скрывается.

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
Page consumes three sections in current MVP read-side:
- `profile` (name, specialization, quote, contacts, client bot username)
- `blocks` (text sections such as about/education/services/reviews)
- `media` (metadata; documents are rendered from items with `media_type=document`)

`reviews` are rendered from `specialist_public_block` with `block_type=reviews`.
`payload.reviews` may stay empty for backward compatibility, but UI does not depend on it.
Документы рендерятся из `media` и показываются только для `media_type=document`.
Если `url` у документа отсутствует (`null`), показывается только название без ссылки.

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
- reviews block in `specialist_public_block` (block_type=`reviews`),
- one media metadata record.

Security guard:
- script hard-stops unless `APP_ENV=dev`.

## Smoke checklist
- `GET /{public_slug}` возвращает HTML со sticky header (`#specialist-sticky-header`) и пунктами меню: «О себе», «Образование», «Документы», «Услуги и цены», «Отзывы», «Записаться».
- Страница делает fetch в `${BASE_URL}/api/public/specialists/{public_slug}` для загрузки контента.
- Loading-state `Загружаем профиль специалиста...` всегда завершается: либо success (`#specialist-page`), либо not-found/error (`#public-specialist-not-found`).
- Fail-safe: runtime JS errors и unhandled promise rejection переводят страницу в not-found/error state (без вечного loading); bootstrap обёрнут как `try { bootstrap().catch(showNotFound) } catch (_) { showNotFound() }`.
- Reserved paths (`/pricing`, `/privacy`, `/terms`, `/revoke-access`, `/api`, `/static`, `/assets`) не перехватываются slug-route.
- Невалидные slug по-прежнему дают 404 на site-route и 400 на API route.


## Post-deploy diagnostic smoke-check (VPS)
Проверка нужна, чтобы убедиться, что production route `GET /{public_slug}` действительно отдаёт **актуальный full-page bridge** из текущего `web_server.py`, а не stale HTML-артефакт.

1. Проверить bridge-маркер `apiBaseUrl` в HTML:
```bash
curl -s https://zumbot.ru/{slug} | grep "const apiBaseUrl"
```
Ожидание: в выдаче есть строка вида `const apiBaseUrl = "https://api.zumbot.ru";` (или текущий `BASE_URL` окружения).

2. Проверить доступность публичного API для опубликованного slug:
```bash
curl -i https://api.zumbot.ru/api/public/specialists/{slug}
```
Ожидание: `HTTP/1.1 200` (или `HTTP/2 200`) и JSON payload профиля.

3. Проверить server-side observability:
- В логах backend присутствует INFO событие
  `event=public_slug_route_rendered slug={slug} route_name=specialist_profile_page api_base_url=...`
- В событии нет персональных данных сверх slug.

4. Проверить завершение loading-state:
- При `200` от API страница переходит в контентный state (`#specialist-page`).
- При runtime ошибке/`!response.ok` страница уходит в not-found state (`#public-specialist-not-found`) без вечной загрузки.
