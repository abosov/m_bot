# Endpoints (MVP)

Документ фиксирует HTTP endpoints, которые реально используются в текущем backend.

## Базовый URL
- Production backend: `https://api.zumbot.ru`.
- В примерах ниже используйте ваш фактический домен.

## 1) Health endpoint

### GET `/healthz`
**Назначение:** liveness-проверка HTTP процесса backend.
**Коды ответа:**
- `200 OK` — сервис отвечает.

**Пример:**
```bash
curl -i "https://api.example.com/healthz"
```

**Ожидаемое тело:**
```json
{"status":"ok","service":"backend"}
```

**Совместимость:** путь `/health` в приложении не зарегистрирован; если он используется во внешней инфраструктуре, требуется proxy alias на `/healthz` (planned/TODO).

## 2) Readiness endpoint

### GET `/readyz`
**Назначение:** readiness-проверка (доступность БД + живость event loop).
**Коды ответа:**
- `200 OK` — backend готов обрабатывать трафик;
- `503 Service Unavailable` — backend не готов;
- `404 Not Found` — endpoint отключён (`ENABLE_READYZ=false`).

**Пример:**
```bash
curl -i "https://api.example.com/readyz"
```

**Ожидаемые тела:**
```json
{"status":"ready","db":"ok","loop":"ok"}
```
или
```json
{"status":"not_ready","db":"fail","loop":"ok","error":"<short_error_type>"}
```

**Совместимость:** путь `/ready` в приложении не зарегистрирован; при необходимости настраивается на уровне proxy как alias на `/readyz` (planned/TODO).

## 3) Telegram personal bot webhook

### POST `/tg/webhook/{bot_id}/{secret}`
**Назначение:** приём update для personal bots (webhook mode).
**Коды ответа:**
- `200 OK` — update принят (включая кейсы с ошибкой внутренней обработки);
- `404 Not Found` — пара `{bot_id}/{secret}` невалидна или bot неактивен.

**Пример:**
```bash
curl -i -X POST "https://api.example.com/tg/webhook/123456789/replace_with_secret" \
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
curl -i "https://api.example.com/google/oauth/callback?code=sample_code&state=00000000-0000-0000-0000-000000000000"
```

## Planned/TODO endpoints

### GET `/health` (planned)
Планируемый alias к `/healthz` для унификации внешних проверок. В текущем коде endpoint отсутствует.

### GET `/ready` (planned)
Планируемый alias к `/readyz` для унификации внешних проверок. В текущем коде endpoint отсутствует.

## Связанные документы
- `docs_!_deployment.md`
- `50_integrations/telegram.md`
- `50_integrations/google_calendar.md`
