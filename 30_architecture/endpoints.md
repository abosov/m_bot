# Endpoints (MVP)

Документ перечисляет внешние HTTP endpoints backend-сервиса.
Цель — зафиксировать публичные точки входа, их назначение и базовые требования.

---

## 0) Базовый URL (production)

В production используем:
- `BASE_URL = https://api.zumbot.ru`
- публичный сайт/лендинг: `https://zumbot.ru`

---

## 1) Telegram Webhook (multi-bot)

### POST /tg/webhook/{bot_id}/{secret}

**Назначение**
Приём Telegram updates для personal bot специалиста.
Master bot в текущем MVP продолжает работать в polling-режиме.

**Текущее состояние реализации**
- endpoint реализован в `web_server.py`;
- проверяет `{bot_id, secret}` по таблице `telegram_bot`;
- принимает только активные боты (`telegram_bot.status = active`);
- передаёт update в отдельный aiogram Dispatcher personal bot.

**Path params**
- `bot_id` — Telegram bot id (`getMe.id`) personal bot.
- `secret` — webhook secret, сгенерированный при подключении и сохранённый в БД.

**Валидация и безопасность**
Backend:
1) ищет `telegram_bot` по `bot_user_id = bot_id`, `webhook_secret = secret`, `status = active`;
2) при несовпадении возвращает `404` (единый ответ без раскрытия деталей);
3) не логирует bot token или secret в открытом виде.

**Request body**
- стандартный Telegram update JSON.

**Response**
- `200 OK` — update принят (даже если внутри handler произошла логическая ошибка);
- `404 Not Found` — неверная пара `{bot_id, secret}` или бот не активен.

Почему `200` при ошибке обработки:
- чтобы избежать бесконечных ретраев Telegram webhook на уже доставленный update.

**Примеры**

```bash
curl -i -X POST "https://api.zumbot.ru/tg/webhook/123456789/your_webhook_secret"   -H "Content-Type: application/json"   -d '{
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

Ожидаемый ответ:
- `HTTP/1.1 200 OK` для валидного webhook URL,
- `HTTP/1.1 404 Not Found` для невалидного `{bot_id, secret}`.

## 2) Google OAuth

### GET /google/oauth/start

**Назначение**
Инициация OAuth-подключения Google для specialist.
Используется из master_bot (онбординг) или из personal bot (переподключение).

**Query params**
- `specialist_id` (или привязка через внутренний session/state)
- `flow` = `onboarding` | `reconnect` (опционально)

**Поведение**
1) генерирует одноразовый `oauth_state` (TTL 10–15 минут)
2) формирует OAuth URL с этим state
3) возвращает URL (обычно как ссылку, которую отправляет бот)

**Response**
- JSON с `auth_url` (если это вызывается не из браузера)
или редирект (если используется напрямую)

`/google/oauth/start` является официальным endpoint MVP.

Текущее состояние реализации:
- endpoint ещё не реализован;
- OAuth URL формируется напрямую в master_bot через `GoogleOAuthService.get_auth_url`.

Он может вызываться:
- напрямую (через браузер),
- либо опосредованно из Telegram-логики.

Это позволяет унифицировать OAuth-флоу и упростить расширение системы.


---

### GET /google/oauth/callback

**Назначение**
Обработка callback от Google после авторизации.

Production callback URL:
`https://api.zumbot.ru/google/oauth/callback`

**Query params**
- `code`
- `state`
- `scope` (может присутствовать)

**Фактическое поведение MVP**
1) валидирует `state` как `specialist_id` (UUID)
2) обменивает `code` на токены
3) сохраняет encrypted `refresh_token` в `google_oauth`
4) сохраняет актуальный набор scopes
5) делает проверку доступа к Calendar API (`calendarList.list`) для ранней диагностики scope
6) отправляет сообщение в Telegram:
   - при успехе: перейти к календарному шагу в master bot
   - при недостатке прав: переподключить Google с re-consent

**Что происходит дальше в Telegram онбординге**
После callback пользователь в master bot выбирает действие:
- `Создать отдельный календарь (рекомендовано)` — MVP
- `Выбрать существующий календарь` — подготовлено сервисно, UI пока stub

Успех календарного шага:
- календарь сохранён,
- smoke-test события create+delete прошёл,
- после этого specialist может быть переведён в `active`.

**Response**
HTML-страница “Google подключен, вернитесь в Telegram”.
---

## 3) Healthcheck / Readiness

### GET /healthz

**Назначение**
Проверка живости backend (liveness): HTTP-сервер запущен и отвечает.
Endpoint доступен во всех средах.

Используется для простых внешних проверок доступности.

**Response**
- `200 OK`
```json
{"status":"ok","service":"backend"}
```

---

### GET /readyz

**Назначение**
Проверка готовности backend к работе (readiness).
В MVP проверяет:
- доступность БД минимальным запросом;
- «живость» event loop через фоновый heartbeat.
Endpoint включается только если `ENABLE_READYZ=true`.
По умолчанию это так в `prod` на VPS, а в `local` — выключено.
Локально `/readyz` отсутствует (404), пока явно не включить
`ENABLE_READYZ=true`.

**Важно:** `/readyz` обязателен для мониторинга в production
(например, UptimeRobot/BetterStack или health-check балансировщика).

**Response**
- `200 OK` — БД доступна и event loop тикает
  ```json
  {"status":"ready","db":"ok","loop":"ok"}
  ```
- `503 Service Unavailable` — БД недоступна и/или event loop не тикает
  ```json
  {"status":"not_ready","db":"fail","loop":"fail","error":"<коротко>"}
  ```

Примечание:
- если проблема только в event loop, поле `db` будет `"ok"`;
- поле `error` возвращается только при ошибке БД (короткий тип ошибки).

---

## 4) Внутренние контракты (не HTTP)

В MVP большая часть “контрактов” — это внутренние сервисные методы,
а не отдельные HTTP endpoints.

Рекомендуемые внутренние методы:

- `TelegramIngress.handle_update(bot_id, update_json)`
- `MasterOnboarding.handle_step(specialist_id, payload)`
- `ClientFlow.show_slots(specialist_id, client_id, period)`
- `ClientFlow.book_slot(specialist_id, client_id, start_at_utc)`
- `ClientFlow.retry_booking(appointment_id)`
- `ClientFlow.cancel_booking(appointment_id)`
- `SpecialistFlow.update_availability(...)`
- `SpecialistFlow.set_duration(...)`

---

## 5) Безопасность endpoints (MVP минимум)

- webhook защищён секретом в URL
- OAuth callback принимает только state, созданный системой
- токены хранятся в зашифрованном виде
- логирование исключает секреты (bot_token, refresh_token)

---

## Связанные документы
- `30_architecture/components.md`
- `50_integrations/telegram.md`
- `50_integrations/google_calendar.md`
- `60_security_and_compliance/secrets.md`
