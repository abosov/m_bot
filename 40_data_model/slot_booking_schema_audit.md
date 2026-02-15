# Аудит схемы БД под новый алгоритм выбора и бронирования слотов (Zumbot MVP)

Источник проверки:
- ORM: `database.py`
- Миграции: `scripts/migrations/*.sql`

## 0) Краткий статус соответствия текущей схеме

1. `appointment.start_at_utc`, `appointment.end_at_utc` — **соответствует**.
2. `appointment.idempotency_key UNIQUE` — **соответствует**.
3. `client(specialist_id, tg_user_id) UNIQUE` — **соответствует**.
4. 3 интервала в `weekly_availability` + парные CHECK на NULL/NULL и `start < end` — **соответствует**.
5. `slot_step_min IN (60,30,15,10)` — **соответствует**.
6. `session_duration_min > 0`, `session_buffer_min >= 0`, `max_sessions_per_day > 0` — **соответствует** (в схеме ограничено строже).
7. `booking_state ∈ {pending, confirmed, failed, cancelled}` — **не соответствует** (сейчас `canceled_by_client`, `canceled_by_specialist`).

---

## 1) Обязательные CHECK constraints

Ниже — список обязательных ограничений, которые должны быть в схеме для корректной работы нового алгоритма.

### specialist_profile
1. `ck_specialist_profile_slot_step_min`
   - `slot_step_min IN (60, 30, 15, 10)`
2. `ck_specialist_profile_session_duration_min`
   - `session_duration_min > 0` (допустимо более строгое ограничение `>= 15`, как сейчас)
3. `ck_specialist_profile_session_buffer_min`
   - `session_buffer_min >= 0`
4. `ck_specialist_profile_max_sessions_per_day`
   - `max_sessions_per_day > 0` (допустимо более строгое ограничение `>= 1`)

### specialist_weekly_availability (в текущей схеме: `weekly_availability`)
5. `ck_weekly_availability_interval_1_pair`
6. `ck_weekly_availability_interval_2_pair`
7. `ck_weekly_availability_interval_3_pair`

Для каждого интервала правило одинаковое:
- разрешены только состояния:
  - `start IS NULL AND end IS NULL` (интервал отключён)
  - `start IS NOT NULL AND end IS NOT NULL AND start < end`
- состояние `start IS NOT NULL AND end IS NULL` запрещено.

### appointment (рекомендуемое обязательное доп. ограничение)
8. `ck_appointment_time_order`
   - `end_at_utc > start_at_utc`

Это ограничение не было явно запрошено в списке требований, но критично для целостности слотов и корректного расчёта пересечений.

---

## 2) Индексы для быстрого read-path

Ниже — минимальный набор индексов для пути чтения «показать слоты / проверить занятость / показать записи».

### Уже должны быть
1. `appointment(idempotency_key)` UNIQUE
   - быстрый idempotency lookup
2. `client(specialist_id, tg_user_id)` UNIQUE (`uq_client_specialist_tg_user_id`)
   - быстрый поиск/апсерт клиента в контексте специалиста
3. `weekly_availability(specialist_id)`
   - базовый доступ к расписанию специалиста

### Нужны дополнительно
4. `weekly_availability(specialist_id, weekday)` UNIQUE
   - гарантирует «одна строка на день недели для специалиста»
   - ускоряет чтение дневного расписания

5. `appointment(specialist_id, start_at_utc)`
   - быстрый выбор диапазона записей специалиста по времени

6. `appointment(specialist_id, booking_state, start_at_utc)`
   - быстрый фильтр занятых слотов по состояниям (`pending`, `confirmed`) в окне дат

7. `appointment(client_id, start_at_utc DESC)`
   - быстрый read-path «мои записи клиента»

Опционально (если PostgreSQL и частичные индексы допустимы):
8. частичный индекс `appointment(specialist_id, start_at_utc) WHERE booking_state IN (...)`
   - уменьшает размер индекса и ускоряет основной путь проверки занятости.

---

## 3) Нужны ли новые поля

### Обязательно
1. В рамках stated требований новые поля **не обязательны** для:
   - `start_at_utc`, `end_at_utc`
   - `idempotency_key`
   - 3 интервалов доступности

### Нужны для согласования статусов отмены
2. Требование задаёт `booking_state ∈ {pending, confirmed, failed, cancelled}`,
   а текущая модель хранит два отдельных статуса отмены (`canceled_by_client`, `canceled_by_specialist`).

Если переходить к единому `cancelled`, для сохранения причины отмены нужен отдельный атрибут:
- `cancelled_by` (например: `client | specialist | system`) **или**
- `cancel_reason` (text/enum)

Иначе теряется аналитика и часть бизнес-сигналов.

---

## 4) Нужна ли миграция (без удаления данных)

Да, нужна.

### План безопасной миграции
1. Проверка и создание отсутствующих CHECK constraints (идемпотентно).
2. Добавление `ck_appointment_time_order` (`end_at_utc > start_at_utc`) после precheck-валидации текущих данных.
3. Добавление индексов read-path:
   - `weekly_availability(specialist_id, weekday)` UNIQUE
   - `appointment(specialist_id, start_at_utc)`
   - `appointment(specialist_id, booking_state, start_at_utc)`
   - `appointment(client_id, start_at_utc DESC)`
4. Нормализация `booking_state` к новому множеству:
   - добавить новый enum value `cancelled` (или новый enum type)
   - обновить существующие строки:
     - `canceled_by_client -> cancelled`
     - `canceled_by_specialist -> cancelled`
   - (если добавлен столбец причины) заполнить `cancelled_by`
5. Обновить ограничения/enum для запрета старых значений.
6. Все DDL — через идемпотентные и backward-safe шаги; без удаления строк.

### Важные prechecks перед миграцией
- дубликаты в `weekly_availability` по `(specialist_id, weekday)`
- строки `appointment` с `end_at_utc <= start_at_utc`
- данные/код, завязанные на старые состояния `canceled_by_*`

