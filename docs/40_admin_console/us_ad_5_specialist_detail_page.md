# US-AD-5 — Specialist Detail Page

Status: Implemented

## User Story

Как `super_admin`  
Я хочу открыть детальную страницу конкретного специалиста в Admin Console  
Чтобы быстро понять текущее состояние специалиста, его настройки и операционные риски без просмотра сырых данных

## Acceptance Criteria

- Доступен UI endpoint `GET /admin/ui/specialists/{specialist_id}` (cookie auth).
- Доступен API endpoint `GET /admin/specialists/{specialist_id}` (`X-API-Key`) для диагностики и поддержки.
- Страница Specialist Detail отображает:
  - базовый профиль (ID, public name, status, created at, timezone, tariff);
  - onboarding state (`master`, `personal`);
  - integration state (`oauth`, `calendar`);
  - operational summary (`clients_count`, `last_activity_at`, `active_7d`).
- При отсутствии специалиста возвращается `404`.
- Для system accounts поведение согласовано с US-AD-4.1:
  - по умолчанию system accounts скрыты;
  - доступ разрешён только при явном `include_system=1`.
- В ответе и UI отсутствуют секреты и персональные данные клиентов.

## Architecture

- Backend слой:
  - добавить read-only use case `GetSpecialistDetailById`;
  - использовать тот же policy-layer фильтрации (`include_system`) что и в списке специалистов.
- HTTP слой:
  - `GET /admin/ui/specialists/{specialist_id}?include_system=0|1`;
  - `GET /admin/specialists/{specialist_id}?include_system=0|1`.
- Источники данных:
  - агрегировать данные из `specialist`, `specialist_profile`, `google_oauth`, `specialist_calendar_settings`, `message_log`, `client`.
- Кэширование для MVP не требуется; single-request aggregation допустима.

## Data mapping (source of truth)

| Field | Source |
|---|---|
| `specialist_id` | `specialist.specialist_id` |
| `public_name` | `specialist_profile.public_name` (fallback: `specialist.specialist_id`) |
| `status` | `specialist.status` |
| `created_at` | `specialist.created_at` |
| `tariff_plan` | `specialist.tariff_plan` |
| `timezone` | `specialist_profile.specialist_timezone` |
| `onboarding_master_done` | `specialist.onboarding_master_completed_at IS NOT NULL` |
| `onboarding_personal_done` | `specialist.onboarding_personal_completed_at IS NOT NULL` |
| `oauth_connected` | `google_oauth.status = 'connected' AND google_oauth.refresh_token_encrypted <> ''` |
| `calendar_selected` | `specialist_calendar_settings.calendar_id <> ''` |
| `clients_count` | `COUNT(client.client_id) WHERE client.specialist_id = specialist.specialist_id` |
| `last_activity_at` | `MAX(message_log.created_at) WHERE message_log.specialist_id = specialist.specialist_id` |
| `active_7d` | `last_activity_at >= now_utc - interval '7 days'` |
| `is_system` | `specialist.is_system` |

## UX (sections layout)

Страница делится на 5 логических секций сверху вниз:

1. **Header**
   - Breadcrumb: `Admin / Specialists / {specialist_id}`
   - Title: `public_name`
   - Meta: `specialist_id`, `status` badge
2. **Identity & Plan**
   - `created_at`, `timezone`, `tariff_plan`
3. **Onboarding**
   - `onboarding_master_done`, `onboarding_personal_done` как badge
4. **Integrations**
   - `oauth_connected`, `calendar_selected` как badge
5. **Operational Summary**
   - `clients_count`, `last_activity_at`, `active_7d`

Состояния экрана:
- loading: skeleton для 5 секций;
- empty/not found: `Specialist not found`;
- error: `Failed to load specialist details` + retry.

## Security rules

- Не возвращать и не рендерить:
  - OAuth токены (`refresh_token_encrypted`, access token, raw token payload);
  - тексты сообщений из `message_log`;
  - PII клиентов (имя, телефон, email, username, message content).
- Разрешены только агрегаты и технические флаги состояния.
- Для UI endpoint использовать cookie-auth; unauthenticated/unauthorized запросы обрабатывать по текущей admin policy (`404` для anti-enumeration).
- Не логировать значения `X-API-Key`, cookie и любые токены интеграций.

## Tests

- Unit:
  - `GetSpecialistDetailById` корректно маппит все поля ответа;
  - `active_7d` корректно считается для `null` и граничных дат;
  - `include_system` корректно блокирует/разрешает system account.
- Integration:
  - `GET /admin/ui/specialists/{id}` требует валидную admin session cookie;
  - `GET /admin/specialists/{id}` требует `X-API-Key`;
  - `404` при несуществующем `specialist_id`;
  - ответ не содержит запрещённых полей (tokens, message text, client PII).
- UI:
  - smoke test рендера 5 секций;
  - loading/empty/error состояния работают.


## Implementation notes

Реализовано в backend/admin UI:

- UI JSON endpoint: `GET /admin/ui/specialists/{specialist_id}` (cookie auth, unauth -> `404`).
- API JSON endpoint: `GET /admin/specialists/{specialist_id}` (`X-API-Key`, wrong/missing key -> `403`).
- HTML page: `GET /admin/specialists/{specialist_id}` (browser request с `Accept: text/html` и валидной cookie `admin_session`; без cookie -> `404`).

Фактическая структура JSON ответа (MVP):

- `basic`:
  - `specialist_id`
  - `public_name`
  - `status`
  - `is_system`
  - `created_at`
  - `tariff_plan`
  - `telegram_username`
  - `telegram_first_name`
- `integration`:
  - `oauth_connected`
  - `calendar_selected`
  - `selected_calendar_id`
  - `timezone`
  - `slot_step`
  - `max_sessions_per_day`
  - `onboarding_master_done`
  - `onboarding_personal_done`
- `activity`:
  - `clients_count`
  - `last_activity_at`
  - `active_7d`
  - `recent_events` (`timestamp`, `event_type`)
- `errors`: массив, для MVP возвращается безопасный список (пустой при отсутствии структурированного источника).

## Definition of Done

- Согласован и зафиксирован API-контракт Specialist Detail (UI + API).
- Реализован backend aggregator с policy `include_system`.
- Реализована страница `/admin/specialists/{specialist_id}` с 5 секциями.
- Добавлены unit, integration и UI smoke tests из раздела выше.
- Пройден security review: подтверждено отсутствие tokens, message text, client PII.
- Обновлена документация Admin Console (`README` + US-AD-5 spec).
