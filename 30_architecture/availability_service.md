# AvailabilityService (MVP): архитектура генерации слотов

## Цель
AvailabilityService отвечает за вычисление доступных стартов сессий для specialist на **следующий календарный день** с учётом:
- weekly availability,
- правил бронирования MVP,
- занятости из Google Calendar,
- длительности сессии, буфера и шага слотов.

Сервис не создаёт события в календаре; он только рассчитывает и возвращает кандидаты слотов.

---

## Ключевые инварианты
1. Все вычисления выполняются в TZ specialist.
2. Все timestamp в БД хранятся в UTC.
3. Google Calendar — источник истины по занятости.
4. Интервалы availability в UI возвращаются в исходном (не merged) виде.
5. `merge_intervals()` используется только:
   - в domain validation,
   - в генерации кандидатов стартов.
6. `session_buffer_min` не материализуется как отдельное Google-событие, но участвует в проверке доступности.
7. Бронирование разрешено только на следующий календарный день и только до 21:00 предыдущего дня в TZ specialist.
8. Если local now specialist > 21:00, следующий день считается недоступным.

---

## Компоненты

### 1) AvailabilityPolicy
Слой бизнес-правил, не зависящий от интеграций:
- проверка окна бронирования (next-day + cutoff 21:00),
- валидация параметров (`slot_step_min ∈ {60,30,15,10}` и т.д.),
- проверка того, что искомая дата действительно next-day в TZ specialist.

### 2) AvailabilityRepository
Читает настройки specialist из БД (UTC + TZ метаданные):
- weekly интервалы (morning/day/evening; каждый может быть `NULL/NULL`),
- `slot_step_min`, `session_duration_min`, `session_buffer_min`, `max_sessions_per_day`,
- TZ specialist.

### 3) CalendarBusyProvider (Google adapter)
Интеграционный слой:
- получает занятые окна на целевой день (и при необходимости с запасом по краям),
- нормализует в внутренний формат busy intervals,
- возвращает только фактическую занятость (Google как truth source).

### 4) IntervalEngine
Доменный движок интервалов:
- нормализация raw-intervals weekly availability (без merge для UI-ответа),
- `merge_intervals()` только для вычислений,
- пересечение/вычитание busy окон,
- проверка влезания `[start, start + duration + buffer]` внутрь свободного окна.

### 5) SlotPrioritizer
Приоритезирует допустимые старты:
1. сначала ближе к началу доступного интервала,
2. затем «стыковка» к confirmed сессиям (минимизация дыр),
3. только старты, кратные `slot_step_min`.

### 6) AvailabilityService (orchestrator)
Собирает pipeline, вызывает все слои, формирует DTO:
- `ui_intervals` (raw, без merge),
- `candidate_slots` (приоритезированный список стартов),
- `meta` (tz, cutoff status, причины недоступности).

---

## Модели данных (концептуально)

### Input (из БД + запроса)
- `specialist_id`
- `specialist_tz` (IANA)
- `target_date_local` (дата в TZ specialist)
- weekly availability intervals:
  - `morning_start_local`, `morning_end_local`
  - `day_start_local`, `day_end_local`
  - `evening_start_local`, `evening_end_local`
- `slot_step_min` (10/15/30/60)
- `session_duration_min` (default 60)
- `session_buffer_min` (default 10)
- `max_sessions_per_day` (default 4)

### Input (из Google)
- `confirmed_busy_intervals` на target day (в TZ specialist после нормализации)

### Output
- `ui_intervals_raw` — исходные интервалы как есть (включая NULL/NULL как disabled)
- `slots` — список `start_local` + UTC эквивалент
- `availability_status`:
  - `OPEN`
  - `CLOSED_AFTER_CUTOFF`
  - `CLOSED_NOT_NEXT_DAY`
  - `CLOSED_LIMIT_REACHED`
  - `CLOSED_NO_FREE_WINDOWS`

---

## Pipeline (шаги 1–8)

### Шаг 1. Resolve context и TZ-нормализация
- Получить specialist settings из БД.
- Вычислить `now_local` в TZ specialist.
- Привести `target_date` к local date specialist.

### Шаг 2. Проверка booking window policy
- Проверить, что `target_date == local_date(now_local) + 1 day`.
- Проверить `now_local.time <= 21:00`.
- Если любое условие нарушено, вернуть `availability_status = CLOSED_*` и пустые слоты.

### Шаг 3. Построение raw availability (для UI)
- Взять morning/day/evening в исходном виде.
- Интервалы `NULL/NULL` пометить disabled.
- Сформировать `ui_intervals_raw` без merge, без сортировочного «склеивания».

### Шаг 4. Domain validation + merge для вычислений
- Отфильтровать disabled интервалы.
- Провалидировать пары start/end (start < end).
- Применить `merge_intervals()` только в вычислительном контуре.
- Результат: `working_intervals_merged`.

### Шаг 5. Загрузка busy из Google (truth source)
- Запросить занятость в Google на target day.
- Нормализовать в TZ specialist.
- Выделить confirmed/занятые интервалы для блокировки слотов.

### Шаг 6. Построение free windows c учётом duration+buffer
- Вычесть busy intervals из `working_intervals_merged`.
- Для каждого потенциального `start` требовать, чтобы
  `[start, start + session_duration_min + session_buffer_min]`
  полностью помещался в свободное окно.
- Буфер использовать только как правило доступности (без создания события).

### Шаг 7. Генерация стартов и приоритезация
- Сгенерировать старты с шагом `slot_step_min`.
- Отбросить старты, нарушающие правило duration+buffer.
- Применить сортировку приоритета:
  1) ближе к началу каждого интервала,
  2) затем старты, стыкующиеся к confirmed сессиям (например, старт ровно после конца busy + buffer, либо окончание ровно перед busy),
  3) стабильный tie-break по local datetime asc.
- Применить ограничение по дневному лимиту (`max_sessions_per_day`) на уровне выдачи/доступности.

### Шаг 8. Формирование ответа
- Вернуть:
  - `ui_intervals_raw` (для отображения),
  - `slots` (prioritized),
  - `status/meta` (cutoff, причины, tz, локальные и UTC представления).
- Для хранения/дальнейших операций использовать UTC, для UI — local TZ specialist.

---

## Приоритеты и edge-cases
- Если интервалы в weekly availability пересекаются, UI всё равно получает исходные 3 блока; merge используется только внутри engine.
- Если Google недоступен, лучше fail-closed (не предлагать слоты), чтобы не нарушить truth source.
- Если уже достигнут `max_sessions_per_day`, возвращать `CLOSED_LIMIT_REACHED`.
- Границы дня считать по TZ specialist, не по UTC.
