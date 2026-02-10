# Components (MVP)

Документ описывает компоненты backend-сервиса и взаимодействие между ними.
Цель — зафиксировать, "где какие скрипты работают", за что отвечают модули,
какие данные читают/пишут и какие внешние API вызывают.

---

## 1. Общая картина

Система состоит из одного backend-сервиса, который обслуживает:
- master_bot (онбординг specialist)
- множество personal specialist_bot (клиентские боты specialist)

Интеграции:
- Telegram Bot API (webhooks + служебные вызовы)
- Google OAuth + Google Calendar API
- Database (хранение состояний и бизнес-логики)

В MVP нет очередей/воркеров. Все операции выполняются в рамках запросов
(включая несколько попыток запросов к Google в рамках одного запроса).

---

## 2. Входные точки (entrypoints)

### 2.1 Telegram webhook endpoint (multi-bot)
- `POST /tg/webhook/{bot_id}/{secret}`

Назначение:
- принимать updates от разных Telegram-ботов
- маршрутизировать обработку в зависимости от:
  - какой бот прислал update (master_bot или personal bot)
  - какая роль у отправителя (specialist owner или client)

### 2.2 Google OAuth callback endpoint
- `GET /google/oauth/callback`

Назначение:
- обработать OAuth callback от Google
- сохранить refresh token
- продолжить онбординг или переподключение календаря

### 2.3 Health/Readiness endpoints
- `GET /healthz`
- `GET /readyz`

Назначение:
- `/healthz` — базовая проверка, что HTTP-сервер отвечает.
- `/readyz` — проверка готовности сервиса: БД отвечает и event loop тикает.
  Если loop tick не обновлялся >12 секунд, `/readyz` возвращает 503.

### 2.4 Observability / Health (наблюдаемость и контроль состояния)
Компонент отвечает за техническую наблюдаемость сервиса и понимание,
что «сервис жив» и «сервис готов к работе».

Включает:
- фоновый heartbeat, который проверяет, что event loop продолжает тикать;
- `GET /healthz` и `GET /readyz` для проверок живости и готовности;
- throttling записи heartbeat в БД через `HEARTBEAT_WRITE_INTERVAL_SEC`;
- логирование технических проверок в таблицы:
  - `service_heartbeats` — результаты `/readyz`;
  - `bot_health_checks` — результаты команд `/status` в master_bot.

Heartbeat throttling (контракт):
- `HEARTBEAT_WRITE_INTERVAL_SEC` задаёт минимальный интервал между записями
  в `service_heartbeats`;
- если `/readyz` вызывается чаще этого интервала и состояние не изменилось,
  новая запись в БД не создаётся;
- heartbeat записывается при первом успешном окне после старта и при последующих
  вызовах, когда истёк throttling-интервал;
- throttling не влияет на HTTP-ответ `/readyz`: readiness-статус рассчитывается на
  каждый запрос, даже если запись в БД пропущена.

Назначение:
- быстро выявлять проблемы с БД или зависанием event loop;
- иметь историю проверок для диагностики инцидентов;
- не перегружать БД частыми heartbeat-вставками.

---

## 3. Telegram Ingress Layer

### 3.1 Webhook Router
Ответственность:
- верифицировать `{bot_id, secret}` по данным в БД
- определить `specialist_id` (для personal bots) или `master_bot` режим
- распарсить update (message/callback_query)
- передать update в handler-слой

Текущее состояние реализации:
- webhook router для personal bots реализован в `web_server.py` на endpoint `/tg/webhook/{bot_id}/{secret}`;
- personal updates передаются в `services/telegram/personal_dispatcher.py`, где определяется роль owner/client;
- master_bot сейчас запускается в режиме polling;
- логирование входящих/исходящих сообщений уже реализовано через middleware (см. `docs/logging.md`).

Вход:
- Telegram update JSON

Выход:
- `RequestContext`:
  - `bot_type` = `master` | `personal`
  - `bot_id`
  - `specialist_id` (для personal)
  - `actor_type` = `super_admin` | `specialist` | `client`
    Примечание: `super_admin` используется только в контексте master_bot.
  - `tg_user_id`
  - `chat_id`
  - локаль/username (если есть)

### 3.2 Master Bot Handler
Ответственность:
- реализовать US-01:
  - регистрация specialist
  - принятие bot_token
  - запуск Google OAuth
  - выбор/создание календаря
  - настройка weekly availability
- работать только в контексте master_bot

Основные вызовы:
- `TelegramService.getMe` (валидация bot_token)
- `TelegramService.setWebhook` (установка webhook личного бота)
- `GoogleOAuthService` (инициация и callback)
- `GoogleCalendarService` (list/create calendars, read timezone)

### 3.3 Personal Bot Handler (общий)
Ответственность:
- принять update от личного бота specialist
- определить actor:
  - owner → specialist-flow (US-02)
  - остальные → client-flow (US-03)

Схема (словами):
- `personal_dispatcher` формирует контекст (`actor`, `specialist_id`, `owner_tg_user_id`, `public_name`);
- корневой personal router делится на sub-router'ы: `common`, `specialist`, `client`;
- на `specialist` router подключён централизованный role-guard;
- guard блокирует любой вызов specialist handler при `actor != specialist` до входа в handler;
- specialist handlers не содержат дублирующих проверок роли в каждом обработчике.

#### Runtime cache personal-ботов (контракт)
Назначение:
- переиспользовать runtime-объекты personal-бота между update, чтобы не создавать
  новый объект на каждый входящий запрос.

Контракт cache:
- cache хранит записи, индексированные по `bot_id`;
- у каждой записи есть TTL (время жизни);
- по истечении TTL запись считается устаревшей и подлежит удалению/переинициализации;
- cleanup выполняется фоново или при очередном обращении к cache (lazy cleanup),
  но поведение должно обеспечивать, что устаревшие записи не живут бесконечно.

Контракт shutdown:
- при graceful shutdown backend обязан закрыть активные сессии runtime personal-ботов;
- после закрытия все объекты cache считаются невалидными;
- при неуспешном закрытии сессии должна быть warning-запись в техническом логе,
  но процесс shutdown не должен раскрывать секреты.

Дальше делегировать в:
- `SpecialistFlowService`
- `ClientFlowService`

---

## 4. Доменные сервисы (Domain Services)

### 4.1 SpecialistFlowService (US-02)
Ответственность:
- изменение weekly availability
- изменение длительности сессии (`session_duration_min`)
- изменение session_buffer_min
- просмотр записей
- отмена записи
- добавление приватной заметки
- переподключение Google/смена календаря (минимально)

Зависимости:
- `AppointmentRepository`
- `AvailabilityRepository`
- `GoogleCalendarService` (update/delete event)
- `TimezoneService` (чтение timezone календаря с TTL)

### 4.2 ClientFlowService (US-03)
Ответственность:
- первый вход: создание/обновление client
- сбор display_name
- смена timezone
- показ слотов (текущая/следующая неделя)
- бронь слота
- retry после failed
- показ “Мои записи”
- отмена записи (>=12 часов)

Зависимости:
- `ClientRepository`
- `AppointmentRepository`
- `AvailabilityService`
- `GoogleCalendarService` (read busy, create/delete event)
- `IdempotencyService`
- `TimezoneService`

---

## 5. Сервисы расчёта слотов и занятости

### 5.1 AvailabilityService
Ответственность:
- генерация candidate slots на основе weekly availability
- применение ограничений:
  - lead time (2h)
  - период недели в TZ клиента (границы периода)
  - длительность сессии
  - минимальный технический перерыв между сессиями
  - шаг 30 минут
- фильтрация кандидатов по занятости из Google

Вход:
- `specialist_id`
- `period_start_utc`, `period_end_utc`
- `session_duration_min`
- `session_buffer_min`
- `slot_step_min=30`

Выход:
- список `slots` (start/end в UTC + представление для TZ client)

### 5.2 TimezoneService
Ответственность:
- получение `specialist_timezone` из Google calendar timezone
- проверка изменения timezone с TTL
- обновление `specialist_profile.specialist_timezone` при изменении

Примечание:
- TTL-проверка чтобы не дергать Google на каждый update

---

## 6. Интеграционные сервисы

### 6.1 TelegramService
Ответственность:
- служебные вызовы Telegram Bot API:
  - `getMe`
  - `setWebhook`
  - `deleteWebhook` (при необходимости)
  - отправка сообщений/редактирование сообщений/answerCallbackQuery

Важно:
- отправка сообщений должна учитывать rate limits Telegram
- желательно использовать retry для отправки (короткие попытки)

### 6.2 GoogleOAuthService
Ответственность:
- формирование OAuth URL
- обработка callback
- хранение refresh_token (encrypted)
- обновление access token при запросах к Google

### 6.3 GoogleCalendarService
Ответственность:
- list calendars
- create calendar
- read calendar timezone
- read busy/free (events or freebusy endpoint)
- create event
- update event (заметка)
- delete/cancel event

MVP особенности:
- операции create event выполняются с несколькими попытками в рамках запроса
- таймауты обязательны

---

## 7. Хранилище данных (Storage Layer)

### 7.1 Repositories
Рекомендуемые репозитории:
- `SpecialistRepository` / `SpecialistProfileRepository`
- `TelegramBotRepository`
- `GoogleOAuthRepository`
- `SpecialistCalendarRepository`
- `WeeklyAvailabilityRepository`
- `ClientRepository`
- `AppointmentRepository`
- `OAuthStateRepository` (одноразовый state для Google OAuth)

### 7.2 Encryption/Secrets
- `bot_token` и `refresh_token` хранятся в зашифрованном виде
- ключи шифрования живут в переменных окружения / секрет-хранилище

---

## 8. Синхронность и влияние задержек (MVP)

Поскольку в MVP нет воркеров:
- все операции выполняются в рамках запросов Telegram webhook
- внешние вызовы (Google) могут быть медленными

Рекомендации:
- использовать сервер с конкурентностью (несколько worker процессов/потоков/async)
- жёсткие таймауты на Google API
- ограниченное число попыток (дефолт 3)

Жёсткое правило MVP:
- обработка одного Telegram update не должна превышать 8–10 секунд
- при превышении лимита:
  - операция прерывается
  - пользователю возвращается сообщение “попробуйте позже”


---

## 9. Связанные документы
- `US-01_specialist_onboarding_master_bot.md`
- `US-02_specialist_manage_settings_in_personal_bot.md`
- `US-03_client_booking_flow.md`
- `20_flows_and_state_machines/*.md`


- Personal bot runtime: `/tg/webhook/{bot_id}/{secret}` + `services/telegram/personal_dispatcher.py` (role detection owner/client).
