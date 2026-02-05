# Roles and Access Control (MVP)

Документ фиксирует модель доступа (authorization) в платформе:
- какие роли существуют,
- как определяется роль в Telegram-ботах,
- какие действия разрешены.

Цель — единые правила для backend и дальнейшего расширения.

---

## 1. Роли

### super_admin
- полный доступ к данным всех specialist и клиентов
- доступ к инфраструктурным операциям (логирование, ключи, мониторинг)
- не участвует в Telegram-диалогах с клиентами (в MVP)

### specialist (owner)
- владелец конкретного specialist-контура (tenant)
- управляет настройками и записями **только** своего specialist
- в MVP: один владелец

### client
- конечный пользователь в рамках одного specialist
- управляет только своими записями в этом контуре

---

## 2. Определение роли в Telegram (MVP)

### 2.1 Master bot
В master_bot все пользователи рассматриваются как потенциальные specialist.
Идентификация происходит по:
- `from.tg_user_id`

Если пользователь уже зарегистрирован как specialist, он продолжает онбординг или управляет переподключением Google.

### 2.2 Личный бот specialist (personal bot)
Для каждого входящего update:

1) backend определяет `specialist_id` по `bot_id` (из webhook URL)  
2) загружает `owner_tg_user_id` для этого specialist  
3) сравнивает `from.tg_user_id` с `owner_tg_user_id`

- если равны → `actor = specialist`
- иначе → `actor = client`

---

## 3. Области доступа (scope)

### 3.1 Specialist scope
`specialist` имеет доступ к:
- `specialist_profile` (изменение публичного имени, длительности, окна отмены — если включено)
- `weekly_availability` (изменение расписания)
- `specialist_calendar` (переподключение/смена календаря)
- `appointments` в рамках своего `specialist_id`
- `clients` в рамках своего `specialist_id`

Ограничения:
- не имеет доступа к данным других specialist
- не имеет доступа к системным настройкам платформы

### 3.2 Client scope
`client` имеет доступ к:
- собственному профилю в рамках `specialist_id` (display_name, timezone)
- своим `appointments` в рамках `specialist_id`
- операциям записи/отмены в пределах правил

Ограничения:
- не имеет доступа к спискам других клиентов
- не имеет доступа к настройкам specialist
- не имеет доступа к инфраструктуре

### 3.3 super_admin scope
`super_admin` имеет доступ к:
- всем specialist, их ботам, календарям, client и appointment
- диагностике и логам
- управлению ключами/конфигурацией (вне Telegram)

---

## 4. Разрешённые действия (MVP)

### 4.1 Client actions
- старт и ввод имени
- просмотр слотов
- создание записи
- retry после failed
- просмотр своих записей
- отмена записи (если >= 12 часов до начала)
- смена timezone клиента (вручную)

### 4.2 Specialist actions (через личный бот)
- просмотр ближайших записей
- отмена записи
- добавление приватной заметки
- изменение weekly availability
- изменение длительности консультации
- переподключение Google / смена календаря (минимально)

### 4.3 System actions (backend)
- валидация bot_token
- установка webhook
- OAuth обмен и хранение refresh_token
- создание/удаление событий в Google
- расчёт слотов с учётом busy/free

---

## 5. Данные и ограничения модели (вариант A)

- `client` идентифицируется уникально по `(specialist_id, tg_user_id)`
- один Telegram пользователь может быть client у нескольких specialist,
  но это будут разные записи `client` (разные `client_id`) в разных контурах

---

## 6. Безопасность (MVP минимум)

- `bot_token` и `refresh_token` хранятся зашифрованно
- webhook защищён секретом в URL: `/tg/webhook/{bot_id}/{secret}`
- проверка, что входящий update принадлежит корректному bot_id:
  backend должен сопоставлять `bot_id` из URL с bot-token в БД и не принимать чужие

---

## 7. Связанные документы
- `00_overview/README.md`
- `00_overview/glossary.md`
- `US-01_specialist_onboarding_master_bot.md`
- `US-02_specialist_manage_settings_in_personal_bot.md`
- `US-03_client_booking_flow.md`
