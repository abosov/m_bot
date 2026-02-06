# Database Schema (MVP)

Документ фиксирует структуру данных платформы.
Все времена в БД хранятся в UTC.

Обозначения:
- PK — primary key
- FK — foreign key
- UQ — уникальность
- IDX — индекс

---

## 1) specialist

### specialist
Хранит тенанта (специалиста) как сущность платформы.

- `specialist_id` UUID (PK)
- `status` enum `specialist.status` NOT NULL
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

IDX:
- `IDX_specialist_status` (`status`)

---

## 2) specialist_auth_telegram

### specialist_auth_telegram
Связь specialist ↔ Telegram-аккаунт в master_bot (кто подключал сервис).

- `specialist_id` UUID (PK, FK → specialist.specialist_id)
- `tg_user_id` bigint NOT NULL
- `tg_username` text NULL
- `tg_first_name` text NULL
- `tg_last_name` text NULL
- `created_at` timestamp NOT NULL

UQ:
- `UQ_specialist_auth_tg_user` (`tg_user_id`)  
  (один Telegram user → один specialist в master_bot)

---

## 3) specialist_profile

### specialist_profile
Профиль и параметры specialist.

- `specialist_id` UUID (PK, FK → specialist.specialist_id)
- `public_name` text NOT NULL
- `owner_tg_user_id` bigint NOT NULL
- `owner_tg_username` text NULL
- `specialist_timezone` text NOT NULL
  (IANA timezone; источник истины = Google calendar timezone)
- `session_duration_min` int NOT NULL DEFAULT 60
- `cancel_window_hours` int NOT NULL DEFAULT 12
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

IDX:
- `IDX_specialist_owner` (`owner_tg_user_id`)

Примечание:
- `owner_tg_user_id` можно копировать из `specialist_auth_telegram.tg_user_id` при онбординге.
- далее используется как основной идентификатор specialist
  при работе через personal bot


---

## 4) telegram_bot

### telegram_bot
Данные о личном Telegram-боте specialist (и master_bot при желании в этой же таблице).

- `telegram_bot_id` UUID (PK)
- `specialist_id` UUID NULL (FK → specialist.specialist_id)  
  (NULL допустим для master_bot, если храним его отдельно)
- `bot_user_id` bigint NOT NULL  (Telegram getMe.id)
- `bot_username` text NOT NULL
- `bot_name` text NOT NULL
- `bot_token_encrypted` text NOT NULL
- `webhook_secret` text NOT NULL
- `webhook_url` text NOT NULL
- `status` enum `telegram_bot.status` NOT NULL
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

UQ:
- `UQ_telegram_bot_user_id` (`bot_user_id`)

IDX:
- `IDX_telegram_bot_specialist` (`specialist_id`)
- `IDX_telegram_bot_status` (`status`)

---

## 5) google_oauth

### google_oauth
Хранит подключение Google OAuth для specialist.

- `specialist_id` UUID (PK, FK → specialist.specialist_id)
- `refresh_token_encrypted` text NOT NULL
- `scopes` text NOT NULL
- `status` enum `google_oauth.status` NOT NULL DEFAULT 'connected'
- `token_updated_at` timestamp NOT NULL
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

---

## 6) specialist_calendar

### specialist_calendar
Выбранный (или созданный) календарь specialist.

- `specialist_id` UUID (PK, FK → specialist.specialist_id)
- `calendar_id` text NOT NULL
- `calendar_title` text NOT NULL
- `calendar_timezone` text NOT NULL  (IANA)
- `source` enum `specialist_calendar.source` NOT NULL
- `timezone_checked_at` timestamp NOT NULL  
  (для TTL-проверки изменения timezone календаря)
- `connected_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

UQ:
- `UQ_specialist_calendar_id` (`calendar_id`)  
  (опционально: если один календарь не может быть привязан к нескольким specialist)

IDX:
- `IDX_calendar_timezone_checked` (`timezone_checked_at`)

---

## 7) weekly_availability

### weekly_availability

- `weekly_availability_id` UUID (PK)
- `specialist_id` UUID (FK → specialist.specialist_id) NOT NULL
- `weekday` smallint NOT NULL  (0..6)
- `is_working` boolean NOT NULL DEFAULT false
- `interval_1_start` time NULL
- `interval_1_end` time NULL
- `interval_2_start` time NULL
- `interval_2_end` time NULL
- `updated_at` timestamp NOT NULL


UQ:
- `UQ_weekly_availability_day` (`specialist_id`, `weekday`)

IDX:
- `IDX_weekly_availability_specialist` (`specialist_id`)

---

## 8) client

### client
Клиент в контуре конкретного specialist (вариант A).

- `client_id` UUID (PK)
- `specialist_id` UUID (FK → specialist.specialist_id) NOT NULL
- `tg_user_id` bigint NOT NULL
- `tg_username` text NULL
- `display_name` text NULL  (короткое имя)
- `client_code` text NOT NULL  
  (короткий код, уникальный в рамках specialist; показывается в календаре)
- `client_timezone` text NOT NULL
- `timezone_source` enum `client.timezone_source` NOT NULL
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

UQ:
- `UQ_client_in_specialist` (`specialist_id`, `tg_user_id`)
- `UQ_client_code_in_specialist` (`specialist_id`, `client_code`)

IDX:
- `IDX_client_specialist` (`specialist_id`)
- `IDX_client_tg_user` (`tg_user_id`)

---

## 9) appointment

### appointment
Запись клиента, с фиксацией состояния и связью с Google event.

- `appointment_id` UUID (PK)
- `specialist_id` UUID (FK → specialist.specialist_id) NOT NULL
- `client_id` UUID (FK → client.client_id) NOT NULL
- `start_at_utc` timestamp NOT NULL
- `end_at_utc` timestamp NOT NULL
- `booking_state` enum `appointment.booking_state` NOT NULL
- `idempotency_key` text NOT NULL
  (формируется на стороне backend
   на основе: specialist_id + client_id + start_at_utc)
- `gcal_event_id` text NULL
- `specialist_private_note` text NULL
- `failure_message` text NULL
  (короткое техническое описание причины failed,
   может использоваться для пользовательского сообщения или логов)
- `created_at` timestamp NOT NULL
- `updated_at` timestamp NOT NULL

UQ:
- `UQ_appointment_idempotency` (`idempotency_key`)

IDX:
- `IDX_appointment_specialist_start` (`specialist_id`, `start_at_utc`)
- `IDX_appointment_client_start` (`client_id`, `start_at_utc`)
- `IDX_appointment_state` (`booking_state`)

Примечания:
- В MVP нет отдельного sync_status, так как нет воркеров.
- `failure_message` используется для диагностики и пользовательского сообщения.

---

## 10) oauth_state (одноразовый state)

### oauth_state
Одноразовый state для Google OAuth, чтобы связать callback с specialist.

- `oauth_state_id` UUID (PK)
- `state` text NOT NULL
- `type` enum `oauth_state.type` NOT NULL
- `specialist_id` UUID (FK → specialist.specialist_id) NOT NULL
- `expires_at` timestamp NOT NULL
- `created_at` timestamp NOT NULL

UQ:
- `UQ_oauth_state` (`state`)

IDX:
- `IDX_oauth_expires` (`expires_at`)

---

## 11) (Опционально) audit_log (MVP+)

### audit_log (опционально, но полезно)
Для наблюдаемости без сложного мониторинга.

- `audit_log_id` UUID (PK)
- `specialist_id` UUID NULL
- `actor_type` text NOT NULL  (`super_admin` | `specialist` | `client` | `system`)
- `actor_tg_user_id` bigint NULL
- `event_type` text NOT NULL
- `event_payload` jsonb NULL
- `created_at` timestamp NOT NULL

IDX:
- `IDX_audit_specialist_time` (`specialist_id`, `created_at`)

---

## 12) message_logs (logging v2)

### message_logs
Техническое логирование входящих/исходящих сообщений Telegram.

- `id` UUID (PK)
- `created_at` timestamp NOT NULL
- `specialist_id` UUID NULL (FK → specialist.specialist_id)
- `bot_id` bigint NOT NULL
- `bot_username` text NULL
- `specialist_name` text NULL
- `tg_user_id` bigint NOT NULL
- `user_handle` text NULL
- `direction` enum `message_logs.direction` NOT NULL
- `message_type` text NOT NULL
- `content` text NULL
- `fsm_state` text NULL
- `handler_name` text NULL
- `is_error` boolean NOT NULL DEFAULT false
- `error_details` text NULL
- `processing_time` float NULL

IDX:
- `IDX_message_logs_bot` (`bot_id`)
- `IDX_message_logs_tg_user` (`tg_user_id`)
- `IDX_message_logs_created_at` (`created_at`)

Примечания:
- Логи не содержат секретов (token/refresh token).
- Поле `direction` принимает значения `IN`/`OUT`.

---

## 13) Минимальные бизнес-ограничения (MVP)
- `lead_time_hours` = 2 (конфиг приложения)
- `slot_step_min` = 30 (конфиг приложения)
- `session_duration_min` на уровне specialist_profile (60/90/120)
- `cancel_window_hours` по умолчанию 12

---

## Связанные документы
- `40_data_model/enums.md`
- `US-01_specialist_onboarding_master_bot.md`
- `US-03_client_booking_flow.md`
- `20_flows_and_state_machines/booking_state_machine.md`
