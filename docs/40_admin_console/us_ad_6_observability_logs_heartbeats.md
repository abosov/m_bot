# US-AD-6 — Observability: Logs + Heartbeats

Status: Planned

## User Story

Как `super_admin`  
Я хочу в Admin Console просматривать логи и heartbeat-события через UI  
Чтобы быстро находить ошибки, контролировать состояние сервисов и проводить базовую диагностику без прямого доступа к сырому backend API

## Acceptance Criteria

- [ ] UI endpoints:
  - `GET /admin/ui/logs` (cookie `admin_session` required; `404` если нет cookie)
  - `GET /admin/ui/heartbeats` (cookie `admin_session` required; `404` если нет cookie)
- [ ] В UI доступна страница/раздел `Logs` с фильтрами: `since/until`, `bot_id`, `specialist_id`, `tg_user_id`, `direction`, `is_error`; пагинация `limit/offset`; `limit` clamp `1..500`
- [ ] В UI доступна страница/раздел `Heartbeats` с фильтрами: `since/until`, `service_name`; пагинация `limit/offset`; `limit` clamp `1..500`
- [ ] Logs в UI всегда redacted (никаких параметров, отключающих redaction в UI)
- [ ] Во всех UI endpoints: `404` если cookie нет/невалидна (не раскрываем существование UI)
- [ ] Добавлены unit tests
- [ ] Обновлены `docs/40_admin_console/README.md` и `docs/40_admin_console/access.md`



## UI (MVP)

В `/admin` добавляется Observability-навигация: `Overview | Specialists | Logs | Heartbeats`.

### Logs section

- Фильтры: `since`, `until`, `bot_id`, `specialist_id`, `tg_user_id`, `direction`, `is_error`, `limit`, `offset`.
- Кнопка `Apply` обновляет данные без перезагрузки страницы (`fetch` с `credentials: same-origin`).
- Таблица: `created_at`, `is_error`, `direction`, `bot_id`, `specialist_id`, `tg_user_id`, `message_type`, `content`, `request_id`.
- Состояния: loading / empty (`No logs found`) / error (`Not available` для `404`).

### Heartbeats section

- Фильтры: `since`, `until`, `service_name`, `limit`, `offset`.
- Таблица: `created_at`, `service_name`, `status`, `details`.
- Состояния: loading / empty (`No heartbeats found`) / error (`Not available` для `404`).

## Endpoint spec (UI)

### GET /admin/ui/logs

- Auth: только cookie `admin_session` (валидная UI session).
- При отсутствии/невалидности cookie: `404` (anti-enumeration).
- Query params: `since`, `until`, `limit`, `offset`, `bot_id`, `specialist_id`, `tg_user_id`, `direction`, `is_error`.
- Response: JSON в формате `{"items": [...], "limit": <int>, "offset": <int>}`.
- Redaction: всегда включён (`redact=true` принудительно; отключение через UI endpoint не поддерживается).



### GET /admin/ui/heartbeats

- Auth: только cookie `admin_session` (валидная UI session).
- При отсутствии/невалидности cookie: `404` (anti-enumeration).
- Query params: `since`, `until`, `limit`, `offset`, `service_name`.
- Response: JSON в формате `{"items": [...], "limit": <int>, "offset": <int>}`.
- Ограничение пагинации: `limit` clamp `1..500`.

## Data / Indexes

Для быстрого чтения в Admin Observability должны быть доступны индексы:

- `message_logs(created_at)`
- `message_logs(is_error, created_at)`
- `message_logs(specialist_id, created_at)`
- `message_logs(bot_id, created_at)`
- `message_logs(tg_user_id, created_at)`
- `service_heartbeats(created_at)`
- `service_heartbeats(service_name, created_at)`

Примечание по совместимости: в текущей схеме `service_heartbeats` может использовать колонку `ts` вместо `created_at`; миграция должна применять эквивалентные индексы безопасно для обоих вариантов.



## Security considerations

- UI endpoints `GET /admin/ui/logs` и `GET /admin/ui/heartbeats` используют только cookie `admin_session` и не должны требовать `X-API-Key`.
- При отсутствии/невалидности cookie возвращается `404` (anti-enumeration), без `401/403`.
- Для `GET /admin/ui/*` при `Accept: text/html` возвращается `404`, чтобы не раскрывать UI JSON API через браузерные ошибки/рендеринг.
- `Logs` в UI всегда redacted; параметр `redact=false` в UI игнорируется.
- Запрещено логировать cookie `admin_session`, `ADMIN_API_KEY`, `ADMIN_UI_PASSWORD`.
- `/admin` и `/admin/*` остаются внутренними endpoint-ами и не должны публиковаться наружу.

## Test coverage

Ключевые test-кейсы US-AD-6 (UI):

- `GET /admin/ui/logs`:
  - auth guard (`404` без cookie, `200` с cookie);
  - redaction всегда включён;
  - фильтры `is_error` и `direction`;
  - пагинация `limit/offset` (включая clamp `1..500`).
- `GET /admin/ui/heartbeats`:
  - auth guard (`404` без cookie, `200` с cookie);
  - фильтр `service_name`;
  - фильтры по времени `since/until`;
  - пагинация `limit/offset` (включая clamp `1..500`).
- Все тесты используют фиксированные `datetime(..., tzinfo=UTC)` для детерминированности.

## Notes

- UI endpoints предназначены только для внутреннего использования Admin Console.
- API-контракты должны оставаться безопасными по умолчанию: без утечки секретов и без выключателей redaction в UI.
