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
Приём Telegram updates от:
- master_bot
- personal bots (боты specialist)

Текущее состояние реализации:
- endpoint ещё не реализован в коде;
- master_bot сейчас работает в режиме polling.

**Path params**
- `bot_id` — Telegram bot id (`getMe.id`) для personal bot.
Master bot в MVP хранится как отдельная запись в таблице `telegram_bot`
(с `specialist_id = NULL`).

Это позволяет:
- использовать единую модель webhook-проверки,
- избежать ветвлений в коде,
- упростить поддержку и расширение.

- `secret` — секрет, генерируемый при подключении бота и хранимый в БД.

**Валидация**
Backend обязан:
1) найти `telegram_bot` по `bot_id`
2) сравнить `secret` из URL с `telegram_bot.webhook_secret`
3) отклонить запрос при несовпадении (404/403)
4) определить тип бота:
   - master_bot (если `bot_id` относится к master_bot),
   - personal bot (если `bot_id` относится к конкретному specialist)

**Request body**
- стандартный Telegram update JSON:
  - message / callback_query / etc.

**Response**
- `200 OK` — при валидном `{bot_id, secret}`
- `403` или `404` — при неверном `{bot_id, secret}`

Примечание:
Telegram ожидает быстрый ответ, но корректный отказ допустим
и не считается ошибкой webhook.

- основная логика может выполняться внутри обработчика, но без длительных блокировок

**Timeout policy (MVP)**
- ограничить длительность обработки
- на Google API ставить таймауты и лимит попыток
- при превышении времени — лучше завершать с сообщением пользователю “попробуйте позже”

---

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

**Поведение**
1) валидирует `state` (должен существовать и быть не просрочен)
2) обменивает `code` на tokens
3) сохраняет `refresh_token` (encrypted) для specialist
4) помечает Google как подключённый
5) продолжает сценарий:
   - запрашивает список календарей
   - либо предлагает выбор, либо создаёт новый календарь
   - фиксирует timezone календаря как `specialist_timezone`

Текущее состояние реализации:
- `state` содержит `specialist_id` напрямую (без таблицы `oauth_state`);
- после сохранения токена backend отправляет специалисту уведомление в Telegram;
- выбор/создание календаря и проверка timezone будут добавлены позже.

**Response**
- в MVP рекомендуется возвращать простую HTML-страницу:
  - “Готово, вернитесь в Telegram”
  - (с инструкцией)
- либо редирект на страницу с таким сообщением

---

## 3) Healthcheck / Readiness

### GET /healthz

**Назначение**
Проверка живости backend (liveness): HTTP-сервер запущен и отвечает.
Endpoint доступен во всех средах.

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
Endpoint включается только в production на VPS
(правило: `prod-only`, `ENABLE_READYZ=true`).
Локально по умолчанию отключён и отсутствует (404).

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
