# US-AD-4 — Specialists Operational Table

Status: Implemented

## User Story

Как `super_admin`  
Я хочу видеть расширенную таблицу по специалистам с техническими статусами и фильтрами  
Чтобы быстро находить проблемных специалистов и понимать, что сломано

## Acceptance Criteria (MVP)

- Таблица `Специалисты` показывает дополнительные колонки:
  - `Timezone` (строка)
  - `Onboarding` (badge: `master/personal done`)
  - `OAuth` (badge: `connected / missing`)
  - `Calendar` (badge: `selected / not selected`)
  - `Active_7d` (badge `yes/no`)
  - `Clients` (число) — уже есть
  - `Tariff` (строка) — уже есть
  - `Last activity` (datetime) — уже есть
- Фильтры (в UI):
  - `status` (уже есть)
  - `include_system` (чекбокс, из US-AD-4.1)
  - `oauth=missing` (переключатель/чекбокс)
  - `calendar=missing` (переключатель/чекбокс)
  - `inactive_days_gt=N` (числовое поле, `N >= 1`)
- По умолчанию: `include_system=false`, остальные фильтры выключены

## Architecture

- UI endpoint: `GET /admin/ui/specialists` (cookie auth)
  - расширить response item полями:
    - `timezone`
    - `onboarding_master_done`
    - `onboarding_personal_done`
    - `oauth_connected`
    - `calendar_selected`
    - `active_7d`
  - поддержать query params:
    - `status`
    - `include_system`
    - `oauth_missing`
    - `calendar_missing`
    - `inactive_days_gt`
    - `limit`
    - `offset`
- (Опционально) синхронизировать те же параметры для `/admin/specialists` (`X-API-Key`) для диагностики

## Request example (implemented)

`GET /admin/ui/specialists?status=active&oauth_missing=1&inactive_days_gt=7&include_system=0`

## Response items (implemented)

Каждый `item` в ответе `/admin/ui/specialists` включает:

- `specialist_id` (`uuid`)
- `public_name` (`string`)
- `status` (`string`)
- `created_at` (`datetime`)
- `tariff_plan` (`string|null`)
- `clients_count` (`number`)
- `last_activity_at` (`datetime|null`)
- `timezone` (`string|null`)
- `onboarding_master_done` (`bool`)
- `onboarding_personal_done` (`bool`)
- `oauth_connected` (`bool`)
- `calendar_selected` (`bool`)
- `active_7d` (`bool`)

## Data definitions (строго)

- `timezone`:
  - брать из `specialist_profile.specialist_timezone` (поле обязательное в текущей схеме)
- `onboarding_master_done`:
  - `TRUE`, если `specialist.onboarding_master_completed_at IS NOT NULL`, иначе `FALSE`
- `onboarding_personal_done`:
  - `TRUE`, если `specialist.onboarding_personal_completed_at IS NOT NULL`, иначе `FALSE`
- `oauth_connected`:
  - `TRUE`, если существует запись в `google_oauth` для `specialist_id`, `refresh_token_encrypted` не пустой и `status = connected`
- `calendar_selected`:
  - `TRUE`, если существует запись в `specialist_calendar_settings` для `specialist_id` и `calendar_id` не пустой
- `active_7d`:
  - `TRUE`, если `last_activity_at >= now_utc - 7 days`
  - `last_activity_at = MAX(message_log.created_at)` по `specialist_id` (если `null` → `active_7d=false`)
- `inactive_days_gt`:
  - если `last_activity_at is null` → считать как `inactive` (т.е. проходит фильтр)
  - иначе `last_activity_at < now_utc - N days`


## Data mapping (source of truth fields)

Короткий data-map по US-AD-4 (текущая схема БД):

- `timezone`:
  - source: `specialist_profile.specialist_timezone`
  - table: `specialist_profile`
  - rule: возвращать как есть (IANA timezone string)

- `oauth_connected`:
  - source: `google_oauth.specialist_id`, `google_oauth.refresh_token_encrypted`, `google_oauth.status`
  - table: `google_oauth`
  - rule: `TRUE`, если есть строка в `google_oauth` для специалиста, `refresh_token_encrypted <> ''`, и `status = 'connected'`; иначе `FALSE`

- `calendar_selected`:
  - source: `specialist_calendar_settings.calendar_id`
  - table: `specialist_calendar_settings`
  - rule: `TRUE`, если есть строка для `specialist_id` и `calendar_id <> ''`; иначе `FALSE`

- `onboarding_master_done`:
  - source: `specialist.onboarding_master_completed_at`
  - table: `specialist`
  - rule: `TRUE`, если `onboarding_master_completed_at IS NOT NULL`; иначе `FALSE`

- `onboarding_personal_done`:
  - source: `specialist.onboarding_personal_completed_at`
  - table: `specialist`
  - rule: `TRUE`, если `onboarding_personal_completed_at IS NOT NULL`; иначе `FALSE`

Поля для этих 5 атрибутов в текущей схеме **доступны**; миграции для MVP data-map не требуются.

## UX

- Фильтры располагаются над таблицей (как `status` сейчас)
- Badges текстовые, без сложного дизайна (пока)
- Empty/error states как сейчас

## Security

- Не добавлять PII (телефоны, email клиентов, тексты сообщений)
- Cookie-auth only for UI endpoints; unauth -> `404`
- Не логировать значения cookie/секретов

## Security review outcome

- Data is operational metadata only, no PII, no message bodies, no tokens.
- Filtering does not expand exposure; access remains admin-only via cookie-auth (`/admin/ui/*`), unauthenticated requests return `404`.
- Logging policy: do not log cookie values; allowed logging includes event names and `request_id`.

## Tests

- Unit/integration:
  - фильтр `oauth_missing` отбирает только специалистов без oauth
  - фильтр `calendar_missing` отбирает только без `calendar_id`
  - `inactive_days_gt` работает для `null last_activity_at` и для даты
  - `include_system` работает совместно с другими фильтрами
- Contract test:
  - новые поля присутствуют в `items`

## Backlog (если данных нет в схеме)

- Для `timezone`, `oauth_connected`, `calendar_selected`, `onboarding_master_done`, `onboarding_personal_done` поля в текущей схеме найдены и описаны в data-map выше.
- Если в будущих изменениях схемы одно из полей исчезнет: фиксировать `Not available in current schema; MVP will not expose; move to backlog` и добавлять миграцию с явным столбцом/связью для восстановления атрибута.
