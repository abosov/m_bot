# Endpoints (MVP)

Документ фиксирует HTTP endpoints, которые реально используются в текущем backend.

## Базовый URL
- Production backend: `https://api.zumbot.ru`.

Проверка с VPS:
```bash
[VPS] curl -i https://api.zumbot.ru/healthz
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

**Ожидаемое тело:**
```json
{"status":"ok","service":"backend"}
```

**Фактическое поведение:** путь `/health` в приложении не зарегистрирован и возвращает `404 Not Found`. Этот путь не используется в production.

## 2) Readiness endpoint

### GET `/readyz`
**Назначение:** readiness-проверка (доступность БД + живость event loop).
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

**Пример:**
```bash
[VPS] curl -i "https://api.zumbot.ru/google/oauth/callback?code=sample_code&state=00000000-0000-0000-0000-000000000000"
```

## Корневой путь backend

### GET `/`
**Фактическое поведение:** возвращает `404 Not Found`, это ожидаемо для backend API в production.

Проверка:
```bash
[VPS] curl -i https://api.zumbot.ru/
```

## Неиспользуемые endpoints

### GET `/health`
В production не используется и возвращает `404 Not Found`.

### GET `/ready`
В production не используется и возвращает `404 Not Found`.

## Связанные документы
- `docs/deployment_readiness.md`
- `50_integrations/telegram.md`
- `50_integrations/google_calendar.md`
