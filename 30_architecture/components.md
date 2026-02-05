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

---

## 3. Telegram Ingress Layer

### 3.1 Webhook Router
Ответственность:
- верифицировать `{bot_id, secret}` по данным в БД
- определить `specialist_id` (для personal bots) или `master_bot` режим
- распарсить update (message/callback_query)
- передать update в handler-слой

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

Дальше делегировать в:
- `SpecialistFlowService`
- `ClientFlowService`

---

## 4. Доменные сервисы (Domain Services)

### 4.1 SpecialistFlowService (US-02)
Ответственность:
- изменение weekly availability
- изменение session_duration
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
  - длительность консультации
  - шаг 30 минут
- фильтрация кандидатов по занятости из Google

Вход:
- `specialist_id`
- `period_start_utc`, `period_end_utc`
- `session_duration_min`
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
