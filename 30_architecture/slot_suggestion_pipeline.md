# Slot Suggestion Pipeline (MVP, US-03)

## 1. Цель и scope

Документ фиксирует целевую архитектуру пайплайна предложения слотов клиенту в personal bot.
Pipeline покрывает путь от запроса клиента «показать доступные слоты» до ответа UI с рекомендациями до 6 слотов.

Ограничения MVP:
- Актуально для MVP: cap выдачи в ранжировании — до 6 слотов.
- multi-tenant (один backend, много specialist-ботов);
- источник истины по расписанию: `weekly_availability` + Google Calendar busy + appointments в БД;
- UI показывает интервалы «утро/день/вечер» в raw-виде (без merge);
- merge используется только в domain validation и генерации валидных стартов;
- буфер (`session_buffer_min`) — только правило расчета, не отдельное Google event.

---

## 2. Входные данные

### 2.1 Domain input (обязательные)
- `specialist_id`
- `client_id`
- `target_date` (дата в TZ specialist, выбранная клиентом)
- `selected_ranges` ⊆ {`morning`, `day`, `evening`}
- `now_utc` (текущее время backend)

### 2.2 Specialist settings
- `specialist_tz`
- `slot_step_min` ∈ {60, 30, 15, 10}
- `session_duration_min` (default 60)
- `session_buffer_min` (default 10)
- `max_sessions_per_day` (default 4)

### 2.3 Availability input
- `weekly_availability` для соответствующего weekday в TZ specialist:
  - до 3 интервалов в день (`morning`, `day`, `evening`)
  - интервал с `start=NULL` и `end=NULL` считается отключенным

### 2.4 Busy input
- Google Calendar busy intervals (`freebusy`)
- Appointment blocks из БД:
  - `confirmed`
  - `pending` (soft lock)

---

## 3. Участвующие сервисы и зоны ответственности

1. **ClientFlowService**
   - оркестрация user-flow (FSM state `choose_slot`),
   - вызов pipeline,
   - форматирование ответа для Telegram UI.

2. **AvailabilityService**
   - построение raw/merged availability на день,
   - генерация кандидатных стартов,
   - доменная валидация вместимости слота,
   - применение buffer/max_sessions/cutoff.

3. **GoogleCalendarService**
   - получение busy intervals из Google Calendar.

4. **AppointmentRepository / BookingPolicyService**
   - чтение внутренних блоков занятости (`confirmed` + `pending`),
   - подсчет числа сессий за день (для `max_sessions_per_day`).

5. **TimezoneService**
   - конвертация `now_utc`, `target_date`, busy-интервалов в TZ specialist.

6. **RankingService (логический слой внутри AvailabilityService или отдельный модуль)**
   - расчет score,
   - сортировка,
   - ограничение выдачи до 6 рекомендаций.

---

## 4. Pipeline 1–N

### Pipeline 1. Request normalization
**Где:** ClientFlowService + TimezoneService  
**Что делает:**
- валидирует вход (`selected_ranges` не пуст, `target_date` корректен),
- определяет `specialist_now` из `now_utc`,
- определяет weekday для `target_date` в TZ specialist.

### Pipeline 2. Cutoff gate
**Где:** AvailabilityService (ранний фильтр)  
**Правило:** запись возможна только при соблюдении окна cancel_window_hours до начала слота.  
**Результат:**
- если условие не выполнено, day отклоняется до тяжелых вычислений;
- UI получает reason-код для fallback (предложить другой день).

### Pipeline 3. Load day availability (raw)
**Где:** AvailabilityService + AvailabilityRepository  
**Что делает:**
- загружает интервалы дня (`morning/day/evening`) как заданы specialist,
- исключает отключенные (`NULL/NULL`) из domain-расчета,
- сохраняет raw-структуру для UI (без merge).

### Pipeline 4. Domain interval normalization (merge)
**Где:** AvailabilityService (только domain layer)  
**Что делает:**
- выполняет merge только для стык-в-стык интервалов (например, 13:00–17:00 + 17:00–21:00),
- не изменяет raw-данные, возвращаемые в UI.

### Pipeline 5. Build busy map
**Где:** GoogleCalendarService + AppointmentRepository, orchestration в AvailabilityService  
**Что делает:**
- получает Google busy/free на `target_date`,
- добавляет `confirmed` + `pending` appointment blocks,
- приводит все интервалы к TZ specialist,
- нормализует/сливает пересечения в unified busy map.

### Pipeline 6. Generate candidate starts
**Где:** AvailabilityService  
**Что делает:**
- внутри merged availability генерирует старты с шагом `slot_step_min`,
- проверяет вместимость: `start + session_duration_min` полностью в одном merged-диапазоне.

### Pipeline 7. Buffer-aware conflict filtering
**Где:** AvailabilityService  
**Что делает:**
- для каждого кандидата строит effective интервал проверки:
  - `candidate_start`
  - `candidate_end = start + session_duration_min`
  - `candidate_block_end = candidate_end + session_buffer_min`
- исключает кандидаты, где `[candidate_start, candidate_block_end)` пересекает busy map.

### Pipeline 8. Max sessions per day gate
**Где:** AvailabilityService + AppointmentRepository/BookingPolicyService  
**Что делает:**
- считает уже существующие сессии дня,
- если лимит `max_sessions_per_day` достигнут, отдает пустой набор + reason `day_limit_reached`.

### Pipeline 9. Range projection for UI bins
**Где:** AvailabilityService  
**Что делает:**
- относит каждый валидный candidate к `morning/day/evening` по времени старта,
- фильтрует по `selected_ranges`,
- не выполняет merge корзин для отображения.

### Pipeline 10. Ranking
**Где:** RankingService  
**Что делает:** считает score кандидатов в рамках каждой выбранной корзины:
1. **Adjacency priority**: максимум за стыковку с busy-блоками через buffer.
2. **Start-of-range priority**: ближе к началу выбранной корзины.
3. **Packing priority**: меньше «дыр» к ближайшей существующей сессии.
4. **Tie-breaker**: более ранний старт.

### Pipeline 11. Cap to up to 6 slots
**Где:** RankingService + ClientFlowService  
**Что делает:**
- по каждой выбранной корзине возвращает:
  - 4 слота, если доступно ≥4,
  - 3 слота, если доступно ровно 3,
  - 1–2 слота, если доступно меньше 3 (с fallback message),
  - 0 слотов — корзина помечается как пустая.

### Pipeline 12. Response assembly + fallback hints
**Где:** ClientFlowService  
**Что делает:**
- формирует Telegram response,
- если корзина пуста — предлагает соседние корзины/другой день,
- если день полностью пуст — предлагает следующий релевантный день.

---

## 5. Где именно применяются ключевые правила

1. **Merge** — только в Pipeline 4 (domain normalization) и далее используется для проверки вместимости в Pipeline 6.
2. **Buffer** — в Pipeline 7, только как расчетное расширение блока (не как Google event).
3. **Google busy/free** — в Pipeline 5 при формировании busy map.
4. **max_sessions_per_day** — в Pipeline 8 до ранжирования.
5. **cutoff** — в Pipeline 2 как ранний gate до загрузки тяжелых интеграционных данных.
6. **Ранжирование** — Pipeline 10.
7. **Ограничение до 6 слотов** — Pipeline 11.

---

## 6. Данные на выходе pipeline

`SlotSuggestionResult` (логический контракт):
- `date`
- `timezone` (specialist)
- `ranges`:
  - `morning`: list[slot]
  - `day`: list[slot]
  - `evening`: list[slot]
- `empty_reasons` по корзинам/дню:
  - `cutoff_blocked`
  - `day_limit_reached`
  - `busy_conflict`
  - `no_availability`
- `fallback_hints`:
  - `suggest_other_ranges`
  - `suggest_next_day`

`slot` содержит минимум:
- `slot_id` (короткий id для callback_data)
- `start_at` (ISO, TZ specialist)
- `end_at` (ISO, TZ specialist)
- `display_label`

---

## 7. Сценарии (2 примера)

### Сценарий A: успешная выдача 4 слотов (стыковка через buffer)

**Дано:**
- Specialist TZ: `Europe/Berlin`
- `target_date`: завтра
- `selected_ranges = {day}`
- availability day: `13:00–17:00`
- `session_duration=60`, `buffer=10`, `slot_step=30`
- busy blocks: `14:10–15:10` (Google), `16:10–17:00` (confirmed)

**Ход pipeline (кратко):**
- Pipeline 2 проходит, если до начала слота >= cancel_window_hours,
- Pipeline 6 генерирует кандидаты: 13:00, 13:30, 14:00, 14:30, 15:00, 15:30, 16:00,
- Pipeline 7 отфильтровывает пересечения с учетом buffer,
- Pipeline 10 поднимает в топ слоты, примыкающие к busy-блокам,
- Pipeline 11 возвращает 4 лучших слота в корзине day.

### Сценарий B: cutoff блокирует день, fallback на следующий

**Дано:**
- Specialist TZ: `Asia/Almaty`
- сейчас `21:35` в TZ specialist,
- клиент пытается записаться на «завтра».

**Ход pipeline (кратко):**
- Pipeline 2 отклоняет `target_date` по cutoff,
- дальнейшие шаги (Google busy, ranking) не выполняются,
- ClientFlowService формирует ответ: «на завтра запись закрыта, выберите послезавтра».

---

## 8. Edge cases

1. **Отключенные интервалы (`NULL/NULL`)**  
   Полностью исключаются из генерации кандидатов, но UI может показывать их как `—`.

2. **Неконсистентный интервал (`NULL/value` или `value/NULL`)**  
   Считается ошибкой данных; интервал не участвует в расчете, пишется warning в технический лог.

3. **Стык интервалов на границе корзин (например, 16:00–17:00 и 17:00–21:00)**  
   Merge разрешен только в domain-слое; в UI корзины остаются отдельными.

4. **Кандидат помещается по длительности, но нарушает buffer**  
   Такой слот исключается (buffer-aware conflict).

5. **Google недоступен/timeout**  
   Fail-closed для бронирования: слоты не показываются как подтвержденно свободные; пользователю отдается «временно недоступно, попробуйте позже».

6. **Достигнут `max_sessions_per_day`, но есть визуально «окна»**  
   Слоты не предлагаются; причина — day limit, а не availability.

7. **Изменение TZ специалиста после сохранения availability**  
   Для расчета всегда используется актуальная `specialist_tz`; day-boundaries и cutoff пересчитываются динамически.

8. **Конкурентный выбор одного слота несколькими клиентами**  
   `pending` учитывается в busy map, чтобы минимизировать гонки до финального confirm.

9. **Выбрано несколько корзин, в одной 0 слотов**  
   Пустая корзина возвращается с reason, остальные корзины показываются в обычном режиме.

10. **Валидных слотов меньше 3**  
   Возвращаются все найденные, UI добавляет fallback-подсказки.
