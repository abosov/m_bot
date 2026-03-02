# Runbook: contact form (`/contacts` → `/public/contact`)

## Назначение

Форма на странице `https://zumbot.ru/contacts` отправляет заявку пользователя на backend endpoint `POST /public/contact`, после чего backend пересылает сообщение на email через SMTP.

## Endpoint

- Method: `POST`
- URL: `/public/contact`
- Auth: не требуется (публичный endpoint)

## Формат запроса

`Content-Type: application/json`

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
- `email` — строка 3..254, базовая проверка email-формата
- `message` — строка 1..4000
- `hp` — honeypot (опционально; для реальных пользователей должно быть пустым)

## Формат ответа

Успех:

```json
{
  "ok": true
}
```

Ошибка (единый формат с коротким кодом):

```json
{
  "ok": false,
  "error": "smtp_not_configured"
}
```

Примеры `error`:
- `validation_error`
- `invalid_json`
- `smtp_not_configured`
- `smtp_send_failed`

## Anti-spam (honeypot)

Поле `hp` используется как honeypot:
- если `hp` непустой, backend возвращает `{"ok": true}`
- SMTP-отправка в этом случае **не выполняется**

## SMTP env-переменные

Обязательные:
- `CONTACT_SMTP_HOST`
- `CONTACT_SMTP_USER`
- `CONTACT_SMTP_PASSWORD`

Опциональные:
- `CONTACT_SMTP_PORT` (по умолчанию `587`)
- `CONTACT_SMTP_FROM` (по умолчанию значение `CONTACT_SMTP_USER`)
- `CONTACT_SMTP_TO` (по умолчанию `info@zumbot.ru`)

## Поведение при отсутствии SMTP-конфига

Если обязательные SMTP env не заданы, endpoint возвращает:

```json
{
  "ok": false,
  "error": "smtp_not_configured"
}
```

И дополнительно отправляет alert через `notify_exception(where="web.contact_form", ...)` для оператора.

## Логирование и приватность

- Логируется событие `contact_form_received` с `request_id` и длинами полей.
- Полный текст `message` в логи и alert-контекст **не пишется**.
- SMTP-секреты (`CONTACT_SMTP_PASSWORD` и т.п.) не должны попадать в логи.

## Проверка

### [ЛОКАЛЬНО]

Запуск unit-тестов (в корне репозитория):

```bash
pytest -q tests/test_public_contact.py
```

При необходимости — полный набор тестов:

```bash
pytest -q
```

### [VPS]

Проверка endpoint с прод-хоста:

```bash
curl -sS -X POST https://zumbot.ru/public/contact \
  -H 'Content-Type: application/json' \
  -d '{"name":"Test","email":"test@example.com","message":"Hello"}'
```

Ожидаемо:
- `{"ok":true}` при корректном SMTP-конфиге;
- `{"ok":false,"error":"smtp_not_configured"}` если SMTP не настроен.
