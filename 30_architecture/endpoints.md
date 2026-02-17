# Endpoints (MVP)

Документ фиксирует HTTP endpoints, которые реально используются в текущем backend.

## Базовый URL
- Production backend: `https://api.zumbot.ru`.
- Public site: `https://zumbot.ru` (не API endpoint).

Проверка с VPS:
```bash
[VPS] curl -i https://api.zumbot.ru/healthz
```


### Зафиксированные health/readiness endpoints в production
- Используются только:
  - `GET /healthz`
  - `GET /readyz`
- `GET /health` и `GET /ready` не используются и возвращают `404 Not Found`.

Проверка legacy путей:
```bash
[VPS] curl -i https://api.zumbot.ru/health
[VPS] curl -i https://api.zumbot.ru/ready
```

## 1) Health endpoint

### GET `/healthz`
**Назначение:** liveness-проверка HTTP процесса backend.
**Коды ответа:**
- `200 OK` — сервис отвечает.

**Пример:**
```bash
[VPS] curl -i "https://api.zumbot.ru/healthz"
```

**Ожидаемое тело (фактический формат):**
```json
{
  "status": "ok",
  "service": "backend",
  "version": "123-abc1234-2026-02-12T00:00:00Z",
  "build_number": 123,
  "commit_sha": "abc1234",
  "build_date_utc": "2026-02-12T00:00:00Z"
}
```

Примечания по полям:
- `build_number` может быть `null`, если файл `VERSION` отсутствует или некорректен.
- `commit_sha` может быть `"unknown"`, если недоступен git metadata.
- `version` формируется как `<build_number|na>-<commit_sha>-<build_date_utc>`.

**Фактическое поведение:** путь `/health` в приложении не зарегистрирован и возвращает `404 Not Found`. Этот путь не используется в production.

## 2) Readiness endpoint

### GET `/readyz`
**Назначение:** readiness-проверка (доступность БД + живость event loop).

**Включение endpoint через `ENABLE_READYZ`:**
- Если `ENABLE_READYZ=true` — route `/readyz` регистрируется.
- Если `ENABLE_READYZ=false` — route `/readyz` не регистрируется и возвращается `404 Not Found`.
- Дефолт зависит от `APP_ENV`:
  - `APP_ENV=prod` → `ENABLE_READYZ=true` (по умолчанию);
  - `APP_ENV=local` (или `dev`/`development`) → `ENABLE_READYZ=false` (по умолчанию).
**Коды ответа:**
- `200 OK` — backend готов обрабатывать трафик;
- `503 Service Unavailable` — backend не готов;
- `404 Not Found` — endpoint отключён (`ENABLE_READYZ=false`).

**Пример:**
```bash
[VPS] curl -i "https://api.zumbot.ru/readyz"
```

**Ожидаемые тела:**
```json
{"status":"ready","db":"ok","loop":"ok"}
```
или
```json
{"status":"not_ready","db":"fail","loop":"ok","error":"<short_error_type>"}
```

**Фактическое поведение:** путь `/ready` в приложении не зарегистрирован и возвращает `404 Not Found`. Этот путь не используется в production.

## 3) Telegram personal bot webhook

### POST `/tg/webhook/{bot_id}/{secret}`
**Назначение:** приём update для personal bots (webhook mode).
**Коды ответа:**
- `200 OK` — update принят (включая кейсы с ошибкой внутренней обработки);
- `404 Not Found` — пара `{bot_id}/{secret}` невалидна или bot неактивен.
- `413 Payload Too Large` — body больше `MAX_WEBHOOK_BODY_BYTES`.

**Пример:**
```bash
[VPS] curl -i -X POST "https://api.zumbot.ru/tg/webhook/123456789/replace_with_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 10001,
    "message": {
      "message_id": 1,
      "date": 1730000000,
      "chat": {"id": 555111222, "type": "private"},
      "from": {"id": 555111222, "is_bot": false, "first_name": "Ivan"},
      "text": "/start"
    }
  }'
```

## 4) Google OAuth callback

### GET `/google/oauth/callback`
**Назначение:** завершение OAuth-подключения Google Calendar.
**Коды ответа:**
- `200 OK` с HTML-страницей (успех);
- `200 OK` с HTML-страницей об ошибке/необходимости переподключения (валидация `state`, `refresh_token missing`, `error` от Google).

Flow `state`: generate/store(TTL) → validate в callback → consume (one-time, удаляется после использования).
`state` не равен `specialist_id` и не должен выводиться в логи как идентификатор пользователя.

**Пример:**
```bash
[VPS] curl -i "https://api.zumbot.ru/google/oauth/callback?code=sample_code&state=00000000-0000-0000-0000-000000000000"
```

## 5) Google Calendar watch webhook

### POST `/integrations/google-calendar/webhook`
**Назначение:** прием push-уведомлений Google Calendar (`watch`) и постановка фоновой задачи reverse-sync без выполнения sync в HTTP-запросе.
**Коды ответа:**
- `200 OK` — всегда (включая неизвестный `channel_id` или неполный набор Google заголовков).

Поведение:
- читает заголовки Google (`X-Goog-Channel-Id`, `X-Goog-Resource-Id`, `X-Goog-Resource-State`, `X-Goog-Message-Number`);
- ищет `specialist_id` + `calendar_id` по `calendar_sync_state.channel_id`;
- добавляет фоновую задачу `run_calendar_reverse_sync(specialist_id, calendar_id)` через in-process `BackgroundTasks`;
- при неизвестном `channel_id` пишет warning и возвращает `200 OK`;
- при отсутствии обязательных заголовков пишет warning и возвращает `200 OK`.

Инициализация watch:
- reverse-sync требует активного Google `events.watch` канала и строки в `calendar_sync_state`;
- канал создаётся автоматически при успешной привязке календаря специалиста в master-onboarding (после выбора существующего календаря и после создания нового);
- webhook адрес для Google watch: `POST /integrations/google-calendar/webhook`.

**Пример:**
```bash
[VPS] curl -i -X POST "https://api.zumbot.ru/integrations/google-calendar/webhook" \
  -H "X-Goog-Channel-Id: sample-channel" \
  -H "X-Goog-Resource-Id: sample-resource" \
  -H "X-Goog-Resource-State: exists" \
  -H "X-Goog-Message-Number: 1"
```

## Корневой путь backend

### GET `/`
**Фактическое поведение:** возвращает `404 Not Found`, это ожидаемо для backend API в production.

Проверка:
```bash
[VPS] curl -i https://api.zumbot.ru/
```

## Неиспользуемые endpoints (legacy)

### GET `/health`
В production не используется и возвращает `404 Not Found` (маршрут отсутствует).

### GET `/ready`
В production не используется и возвращает `404 Not Found` (маршрут отсутствует).

## Связанные документы
- `docs/deployment_readiness.md`
- `50_integrations/telegram.md`
- `50_integrations/google_calendar.md`
