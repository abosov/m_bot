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
- В кодовой базе должен оставаться только browser-safe runtime bridge (без `?.` и `??`), legacy/browser-unsafe варианты удалены и не должны дублироваться в других route-ветках.
- Legacy minimal-шаблон (только name/specialization/quote) больше не используется.
- Legacy DOM IDs `specialist-loading`, `specialist-not-found`, `specialist-content` в runtime-странице отсутствуют; используются `public-specialist-loading`, `public-specialist-not-found`, `specialist-page`.
- Если slug валиден, но профиль не найден/не опубликован, страница показывает site-level not found state.
- Невалидные slug и non-slug пути не перехватываются и обрабатываются обычным routing сайта.

## Styles integration for `GET /{public_slug}`
- Site base styles are served from static file `/assets/styles.css` (`web/assets/styles.css`).
- Specialist landing styles are served from dedicated static file `/assets/specialist.css` (`web/assets/specialist.css`).
- The specialist stylesheet is linked only on the slug bridge route in `web_server.py` (`@app.get("/{public_slug}")`), preserving single full-page bridge and avoiding inline CSS.
- Current asset pipeline for specialist page is static-file based: `/assets/specialist.css` is assembled from:
  - `frontend/styles/layout.css`
  - `frontend/styles/specialist.css`

### Mandatory specialist CSS selectors (runtime contract)
`/assets/specialist.css` must contain rules for:
- `.specialist-page`
- `.specialist-page--hidden`
- `.specialist-header`
- `.specialist-header__inner`
- `.specialist-hero`
- `.hero-grid`
- `.profile-photo`
- `.specialist-subnav`
- `.specialist-subnav__link`
- `.specialist-subnav__link--active`
- `.section`
- `.container`
- `.section-card`
- `.services-grid`
- `.service-card`
- `.reviews-grid`
- `.review-card`
- `.cta-final`
- `.specialist-hidden`

### Mandatory runtime refs for sticky subnav
Inline runtime bridge must define `sectionNavEl` and `subnavListEl` before usage:
- `const sectionNavEl = document.getElementById('specialist-section-nav');`
- `const subnavListEl = sectionNavEl ? sectionNavEl.querySelector('.specialist-subnav__list') : null;`

Sticky-nav helpers must be guarded:
- `if (!sectionNavEl || !subnavListEl) return;`

## Public page visual order
1. Sticky header (identity + компактная CTA)
2. Hero (desktop: 2 колонки, mobile/tablet: 1 колонка)
3. Sticky section navigation (pill tabs + active section tracking)
   - фото в контейнере с фиксированной пропорцией **4:5** (`aspect-ratio: 4 / 5`, `object-fit: cover`)
   - справа: имя, специализация, quote-card (если есть), primary CTA и contacts pills
4. О себе
5. Образование
6. Документы
7. Услуги и цены
8. Отзывы
9. Нижний CTA-блок «Записаться»

Если фото отсутствует, рендерится визуальный placeholder-card той же пропорции 4:5.
Если цитата пустая, quote-card не рендерится.
Все контентные секции визуально унифицированы: max-width контейнер, card-style и единая типографическая иерархия.

### Responsive правила
- **Desktop >=1200px**: комфортный 2-колоночный hero + sticky section nav с pills.
- **Tablet 768–1199px**: header/hero уплотняются, subnav остаётся в одну строку с горизонтальным скроллом при необходимости.
- **Mobile <768px**: hero в 1 колонку, фото занимает всю ширину колонки и сохраняет 4:5; sticky subnav остаётся usable пальцем и не вызывает overflow страницы.

### Sticky section navigation UX
- Subnav рендерится отдельным sticky-блоком `#specialist-section-nav` сразу после hero.
- Subnav использует chips/pills вместо plain-links и поддерживает `hover`, `focus-visible`, `active` states.
- Active section определяется через `IntersectionObserver` (стабильный выбор по видимости и позиции).
- На tablet/mobile subnav становится горизонтально прокручиваемым контейнером; активный пункт автоматически подводится в видимую область.
- В subnav CTA "Записаться" остаётся на desktop, а на mobile скрывается для снижения визуальной перегрузки.
- Для предотвращения перекрытия заголовков якорных секций используются runtime-offset variables (`--specialist-sticky-offset` на базе высоты header + subnav).


## Runtime bridge state model (single-bridge)
- Для `GET /{public_slug}` используется **один** канонический full-page bridge из `web_server.py`.
- В DOM существуют только 3 root-state контейнера:
  - `#specialist-page` — success;
  - `#public-specialist-loading` — loading;
  - `#public-specialist-not-found` — not-found/error.
- Runtime script переключает state через единый `setRuntimeState(state)` и гарантирует взаимоисключаемость состояний (в каждый момент времени видим только один root-state).
- Runtime bridge хранит явное состояние `let runtimeState = 'loading'`; `setRuntimeState(state)` всегда синхронно обновляет `runtimeState`, DOM visibility и диспатчит `public-specialist-state-change` c `detail.state`.
- Initial state: visible только loading (`setRuntimeState('loading')`).
- Success state: после `fetch(...).ok` выполняется `setRuntimeState('success')`.
- Error state: при `!response.ok`, runtime exception до success-state, `window.error` или `unhandledrejection` во время bootstrap выполняется `setRuntimeState('not-found')` через единый `showNotFound()`.
- Watchdog используется только как защита от вечного loading: таймер стартует в начале bootstrap и очищается автоматически при любом терминальном состоянии (`success` или `not-found`).
- Правило терминальности: `success` не должен самопроизвольно переходить в `not-found` без нового запроса/явного перезапуска bootstrap.
- Bootstrap обязательно обёрнут в `try/catch`; аварийный fallback: `showNotFound()`.
- Legacy minimal-template удалён и не должен сосуществовать с full-page bridge.

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
- Mobile smoke-check: открыть `/{public_slug}` в older mobile browser / embedded webview и убедиться, что runtime-bridge исполняется (страница уходит из loading в success/not-found), а inline script не содержит `?.` и `??`.
- Fail-safe: runtime JS errors и unhandled promise rejection переводят страницу в not-found/error state только пока runtime находится в `loading`; после `success` глобальный bootstrap fail-safe больше не должен скрывать профиль.
- Browser compatibility requirement: inline runtime bridge для `GET /{public_slug}` должен использовать browser-safe синтаксис без optional chaining (`?.`) и nullish coalescing (`??`), чтобы не ломаться в older mobile browsers / embedded webviews на parse-time.
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
