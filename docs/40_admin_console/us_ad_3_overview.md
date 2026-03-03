# US-AD-3: Admin Overview (MVP)

Status: Implemented

## User Story

Как `super_admin`  
Я хочу видеть сводку по системе на `/admin`  
Чтобы за 1 минуту понять состояние продукта

---

## Acceptance Criteria

- На `/admin` сверху отображается блок **Overview** со следующими метриками:
  - `specialists_total`
  - `specialists_active_7d`
  - `clients_total`
  - `errors_24h`
  - `server_time_utc`, `env`, `version` (эти поля уже присутствуют на странице и остаются видимыми в блоке состояния системы)
- Значения метрик загружаются через отдельный UI endpoint, доступный только при валидной admin session cookie.
- Для блока Overview реализованы состояния:
  - `loading`
  - `error`
  - `loaded`
- В блоке Overview и API-ответах не выводятся PII-поля (телефоны, email пользователей, тексты сообщений).
- Для `errors_24h`: если ошибок нет **или** источник ошибок недоступен/не определён, в MVP возвращается `0`.

---

## Architecture (components + endpoints)

### Components

- **Admin Page (`GET /admin`)** — существующая страница админ-консоли, где размещается UI-блок Overview в верхней части.
- **Overview UI Data Provider (`GET /admin/ui/overview`)** — новый endpoint для браузерного запроса из `/admin`, использует cookie-auth (`admin_session`).
- **Overview Aggregation Service (backend layer)** — вычисляет агрегированные метрики из таблиц `specialists`, `clients`, `message_log` и источника ошибок (если доступен).
- **(Optional) Diagnostics API (`GET /admin/overview`)** — опциональный endpoint под `X-API-Key` для curl/ops-диагностики, если будет нужен отдельно от UI.

### Endpoints

- `GET /admin` — уже существует (страница).
- `GET /admin/ui/overview` — обязателен в рамках US-AD-3.
  - Auth: cookie `admin_session`.
  - Unauthorized: `404`.
  - Response (200, JSON):

```json
{
  "specialists_total": 123,
  "specialists_active_7d": 58,
  "clients_total": 987,
  "errors_24h": 0,
  "computed_at_utc": "2026-01-20T12:00:00Z",
  "env": "prod",
  "version": "1.4.2"
}
```

- `GET /admin/overview` — опционально (если нужен для диагностики).
  - Auth: `X-API-Key`.
  - Payload идентичен `GET /admin/ui/overview`.

---

## Implementation notes

- Реализован UI endpoint: `GET /admin/ui/overview`.
- Авторизация: cookie `admin_session` (тот же guard, что и для `/admin`/`/admin/ui/specialists`); без валидной cookie возвращается `404`.
- Текущий response payload:
  - `specialists_total`
  - `clients_total`
  - `specialists_active_7d`
  - `errors_24h`
  - `computed_at_utc`
  - `env`
  - `version`
- Ограничение MVP: `errors_24h = 0`, так как в текущей реализации не подключён выделенный источник ошибок; требуется отдельная backlog-задача на интеграцию реального error store.

---

## Data model impact

- **No DB migrations.**
- Используются существующие таблицы/источники данных:
  - `specialists`
  - `clients`
  - `message_log` (или эквивалентный лог активности сообщений)
- Для MVP агрегация выполняется runtime-запросами.

---

## Metric definitions (strict)

- `specialists_total`
  - Определение: `COUNT(*)` по таблице `specialists`.
  - Тип: integer (`>= 0`).

- `clients_total`
  - Определение: `COUNT(*)` по таблице `clients`.
  - Тип: integer (`>= 0`).

- `specialists_active_7d`
  - Определение: количество специалистов, для которых `last_activity_at >= now_utc - interval '7 days'`.
  - `last_activity_at` определяется как `MAX(message_log.created_at)` по каждому специалисту.
  - Специалист без записей в `message_log` считается **неактивным**.
  - Тип: integer (`>= 0`, `<= specialists_total`).

- `errors_24h`
  - Определение: количество записей ошибок за последние 24 часа из существующего источника ошибок.
  - MVP-решение при отсутствии явного источника ошибок: `errors_24h = 0`.
  - Для MVP фиксируется backlog-задача: **подключить реальный источник ошибок и заменить заглушку `0` на фактический подсчёт**.
  - Тип: integer (`>= 0`).

- `computed_at_utc`
  - Определение: текущее серверное UTC-время в формате ISO-8601.

- `env`
  - Определение: строковый идентификатор окружения приложения (`dev`/`stage`/`prod` и т.п.).

- `version`
  - Определение: версия backend-сборки, отображаемая в админ-консоли.

---

## UX (layout + states)

### Layout

- Блок Overview размещается **вверху страницы `/admin`, над навигацией**.
- Формат отображения:
  - компактный карточный `2x2` для ключевых счётчиков (`specialists_total`, `specialists_active_7d`, `clients_total`, `errors_24h`),
  - или одна горизонтальная строка на широких экранах.
- Технические поля `server_time_utc`, `env`, `version` остаются видимыми в верхней области статуса системы.

### States

- `loading`: отображается текст **"Loading overview…"**.
- `error`: отображается текст **"Failed to load overview"**.
- `loaded`: отображаются рассчитанные значения метрик.

---

## Security (access + data exposure)

### Access control

- `GET /admin/ui/overview` доступен только при валидной cookie admin session.
- При отсутствии/невалидности cookie endpoint возвращает `404`.

### Data exposure

- В ответе endpoint-а отсутствуют секреты и токены.
- Не возвращаются PII-поля:
  - телефоны,
  - email,
  - тексты сообщений.
- Логирование значений метрик допустимо как operational telemetry, но запрещено логировать cookies/tokens.

---

## Tests (unit/integration)

### Unit tests

- Проверка корректности вычисления `specialists_active_7d`:
  - учитываются только специалисты с `MAX(message_log.created_at) >= now_utc - 7d`.
  - специалисты без логов не считаются активными.
- Проверка fallback-поведения `errors_24h = 0` при отсутствии/недоступности источника ошибок.

### Integration tests

- При валидной cookie: `GET /admin/ui/overview` возвращает `200` и JSON с ключами:
  - `specialists_total`
  - `specialists_active_7d`
  - `clients_total`
  - `errors_24h`
  - `computed_at_utc`
  - `env`
  - `version`
- Без cookie: `GET /admin/ui/overview` возвращает `404`.
- Корректность расчёта на тестовой БД:
  - при 2 специалистах и заданных логах получаются ожидаемые `specialists_total` и `specialists_active_7d`.

---

## Security review outcome

- **Access:** endpoint `GET /admin/ui/overview` доступен только по валидной admin session cookie; при неуспешной авторизации возвращается `404` (anti-enumeration).
- **Data exposure:** response содержит только агрегированные метрики и технические поля (`env`, `version`, `computed_at_utc`), без PII и без message bodies.
- **Logging:** запрещено логировать cookies/tokens; допустимо логировать имена событий (event names) и технический контекст без секретов.
- **Backlog:** при подключении реального источника для `errors_24h` необходимо отдельно проверить, что источник и его трансформации не раскрывают чувствительные payloads.

---

## Documentation updates required

- Обновить `docs/40_admin_console/README.md`: перенести US-AD-3 в раздел Implemented и добавить endpoint `GET /admin/ui/overview` в обзор endpoint-ов.
- Поддерживать актуальность контракта `GET /admin/ui/overview` при изменении состава метрик/полей ответа.
