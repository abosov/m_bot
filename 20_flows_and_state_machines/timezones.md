# Timezones (MVP)

Документ описывает правила работы с часовыми поясами в платформе:
- откуда берётся timezone specialist,
- как определяется timezone client,
- как считаются границы недели,
- как отображается время пользователям.

---

## 1. Общие принципы

1) Telegram не предоставляет timezone пользователя.
2) Источник истины для timezone specialist — Google Calendar timezone выбранного календаря.
3) Все времена в базе данных хранятся в UTC.
4) Для пользователя время отображается в его timezone (client_timezone или specialist_timezone).
5) Границы недели для показа слотов считаются в timezone клиента.

---

## 2. Timezone specialist (источник истины = Google)

### 2.1 При подключении календаря
- backend считывает timezone выбранного/созданного календаря в Google
- записывает это значение как `specialist_timezone`
- если specialist ранее выбирал иной timezone в онбординге:
  - backend информирует, что timezone берётся из Google
  - для изменения timezone требуется изменить его в Google

### 2.2 Проверка изменения timezone календаря
В MVP backend проверяет timezone календаря с ограничением частоты (TTL),
чтобы не выполнять лишние запросы к Google API.

Рекомендованная политика:
- хранить `specialist_calendar.timezone_checked_at`
- при обращении к календарю:
  - если `now - timezone_checked_at > TTL` (например 6 часов),
    выполнить запрос к Google и сверить timezone
  - при изменении:
    - обновить `specialist_timezone`
    - обновить `timezone_checked_at`
    - зафиксировать изменение (лог)
    - сообщить specialist при ближайшем взаимодействии (MVP-минимум)

---

## 3. Timezone client (MVP)

### 3.1 Значение по умолчанию
При первом входе клиента:
- `client_timezone = specialist_timezone`
- `timezone_source = default_from_specialist`

### 3.2 Изменение вручную
Клиент может изменить timezone через действие «Сменить часовой пояс».
При изменении:
- `client_timezone` обновляется
- `timezone_source = client_selected`

---

## 4. Границы периода показа слотов

### 4.1 Cutoff-правило записи (cancel_window_hours (default 12h))
Запись и изменение доступны только при соблюдении окна cancel_window_hours до начала слота и только
при соблюдении окна cancel_window_hours в timezone specialist.

Правило рассчитывается в TZ specialist:
- доступна запись на любые будущие даты в пределах периода, если до начала слота >= cancel_window_hours;
- слоты ближе окна cancel_window_hours недоступны независимо от календарного дня.

### 4.2 Период “текущая неделя до конца”
Период вычисляется в timezone клиента:
- `period_start_client` определяется с учётом cutoff-правила в TZ specialist и затем конвертируется в TZ клиента
- `period_end_client = end_of_week_client (воскресенье 23:59:59)`

Далее границы конвертируются в UTC для запросов к Google и хранения.

### 4.3 “Следующая неделя”
По запросу клиента:
- период = следующая календарная неделя целиком в timezone клиента
- границы конвертируются в UTC

---

## 5. Генерация слотов и конвертация времени

### 5.1 Генерация в координатах specialist
Weekly availability задана в координатах timezone specialist.
Поэтому базовая генерация candidate slots выполняется в timezone specialist,
после чего применяется фильтрация по:
- cutoff-правилу cancel_window_hours (default 12h) (TZ specialist),
- шагу `slot_step_min ∈ {60,30,15,10}` (дефолт 15),
- длительности сессии (дефолт 60) и буферу (дефолт 10, только правило расчёта слотов, не отдельное Google-событие),
- склейка стык-в-стык интервалов выполняется только для domain-валидации слота и генерации доступных стартов; UI (когда предлагает выбрать «утро/день/вечер») показывает интервалы в исходном виде (как их задал специалист),
- исключению отключённых интервалов availability (`start=NULL` и `end=NULL`) из клиентского отображения и из генерации слотов,
- лимиту `max_sessions_per_day` (дефолт 4),
- границам периода (UTC),
- занятости Google Calendar (UTC).

### 5.2 Отображение клиенту
Слот отображается в timezone клиента (`client_timezone`).

Если `client_timezone != specialist_timezone`:
- рядом отображается время в timezone specialist.

---

## 6. Хранение времени в данных

### 6.1 В базе данных
- `appointment.start_at_utc` (UTC)
- `appointment.end_at_utc` (UTC)

### 6.2 В интерфейсе
Время конвертируется в локальную TZ:
- client: `client_timezone`
- specialist: `specialist_timezone`

---

## 7. Ошибки и крайние случаи (MVP)

- Если timezone календаря в Google изменился:
  - система обновляет `specialist_timezone`
  - пользователям показываются времена по актуальному значению

- Если client вручную выбрал неверный timezone:
  - система отображает слоты в выбранной TZ
  - (дополнительно) рядом показывает время specialist, чтобы снизить риск ошибки

---

## 8. Связанные документы
- `US-01_specialist_onboarding_master_bot.md`
- `US-03_client_booking_flow.md`
- `00_overview/glossary.md`
