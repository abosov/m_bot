# Runbook: contact form (`/contacts` → `/public/contact`)

## 1) Что делает форма и какой endpoint вызывает

Страница `/contacts` отправляет контактную заявку пользователя в backend на публичный endpoint:

- Method: `POST`
- URL: `/public/contact`
- `Content-Type: application/json`
- Auth: не требуется

### JSON schema запроса

Пример:

```json
{
  "name": "Иван",
  "email": "ivan@example.com",
  "message": "Хочу подключить бота",
  "hp": ""
}
```

Поля:
- `name` — строка 1..80
- `email` — строка 3..254, базовая валидация email
- `message` — строка 1..4000
- `hp` — honeypot (для реального пользователя должно быть пустым)

### JSON schema ответа

Успех:

```json
{
  "ok": true
}
```

Ошибка:

```json
{
  "ok": false,
  "error": "smtp_not_configured"
}
```

Типичные `error`:
- `invalid_json`
- `validation_error`
- `smtp_not_configured`
- `smtp_send_failed`

### Honeypot `hp`

Anti-spam поведение:
- если `hp` непустой (например, `"spam"`), backend сразу возвращает `{"ok": true}`;
- SMTP-отправка в этом случае не выполняется.

## 2) Какие env нужны на VPS (systemd)

Ниже пример для `EnvironmentFile` (например, `/etc/zumbot/backend.env`):

```env
CONTACT_SMTP_HOST=smtp.beget.com
CONTACT_SMTP_PORT=2525
CONTACT_SMTP_USER=info@zumbot.ru
CONTACT_SMTP_PASSWORD=...
CONTACT_SMTP_FROM=info@zumbot.ru
CONTACT_SMTP_TO=info@zumbot.ru
```

Важно:
- обязательные: `CONTACT_SMTP_HOST`, `CONTACT_SMTP_USER`, `CONTACT_SMTP_PASSWORD`;
- на VPS часто блокируют 25/587; для Beget используйте `smtp.beget.com:2525`;
- `CONTACT_SMTP_PORT` — рекомендован `2525`;
- `CONTACT_SMTP_FROM` — опционально (по умолчанию берётся `CONTACT_SMTP_USER`);
- `CONTACT_SMTP_TO` — по умолчанию `info@zumbot.ru`;
- `CONTACT_SMTP_TIMEOUT_SECONDS` — опционально, по умолчанию `10`.

Пример в unit-файле systemd:

```ini
[Service]
EnvironmentFile=/etc/zumbot/backend.env
```

После изменения env:

Пример connect-check до SMTP (с VPS):

```bash
python - <<'PY'
import socket
with socket.create_connection(("smtp.beget.com", 2525), timeout=10) as sock:
    print("connected", sock.getpeername())
PY
```


```bash
sudo systemctl daemon-reload
sudo systemctl restart zumbot-backend
```

## 3) Как проверить

### [ЛОКАЛЬНО]

Быстрая проверка тестов контракта contact endpoint:

```bash
pytest -q tests/test_public_contact.py
```

Можно также прогнать весь набор:

```bash
pytest -q
```

### [VPS]

Пример ручной проверки endpoint:

```bash
curl -sS -X POST https://zumbot.ru/public/contact \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test","email":"test@example.com","message":"Hello from VPS","hp":""}'
```

Ожидаемые ответы:
- `{"ok":true}` — SMTP настроен, отправка прошла;
- `{"ok":false,"error":"smtp_not_configured"}` — не хватает SMTP env;
- `{"ok":false,"error":"smtp_send_failed"}` — SMTP настроен, но отправка не удалась.

Проверка honeypot на VPS:

```bash
curl -sS -X POST https://zumbot.ru/public/contact \
  -H 'Content-Type: application/json' \
  -d '{"name":"Bot","email":"bot@example.com","message":"spam","hp":"spam"}'
```

Ожидаемо: `{"ok":true}` (без SMTP-отправки).

## 4) Безопасность и логирование

- Логируется событие `contact_form_received` с `request_id` и длинами полей (`name_len`, `email_len`, `message_len`, `hp_len`).
- Перед отправкой логируется `contact_form_smtp_attempt` с `request_id`, `host`, `port`, `timeout` (без секретов).
- Полный текст `message` не логируется (используются только длины).
- SMTP-секреты (`CONTACT_SMTP_PASSWORD`) не должны попадать в логи/алерты.
