# US-AD-2: Specialists list dashboard (MVP)

## User Story

Как `super_admin`
Я хочу видеть список специалистов в Admin Console
Чтобы быстро оценивать состояние онбординга и активности специалистов

---

## Acceptance Criteria

- [ ] Доступен endpoint `GET /admin/specialists?limit=&offset=&status=&tariff_plan=&active_since_hours=`.
- [ ] Endpoint возвращает список специалистов с полями:
  - `specialist_id`
  - `public_name`
  - `status`
  - `created_at`
  - `onboarding_master_completed_at`
  - `onboarding_personal_completed_at`
  - `tariff_plan`
  - `clients_count`
  - `last_activity_at` (nullable)
- [ ] Поддерживается фильтрация по `status`, `tariff_plan`, `active_since_hours`.
- [ ] Поддерживается пагинация через `limit` и `offset`.
- [ ] В Admin Console реализован табличный вывод с отдельными состояниями loading / empty / error.

---

## Architecture

### Components involved

- Backend Admin API (`/admin/specialists`) для выдачи агрегированных данных по специалистам.
- Admin Console UI: экран со списком специалистов (таблица + фильтры).
- Источники данных:
  - таблица специалистов (базовые данные и статус);
  - таблица `Client` (агрегация количества клиентов);
  - таблица `MessageLog` (определение времени последней активности).

### API changes

**Endpoint:** `GET /admin/specialists`
**Query params:**
- `limit` (int, optional)
- `offset` (int, optional)
- `status` (string, optional)
- `tariff_plan` (string, optional)
- `active_since_hours` (int, optional)

**Response (200):**

```json
{
  "items": [
    {
      "specialist_id": "sp_123",
      "public_name": "Анна",
      "status": "active",
      "created_at": "2026-01-10T12:00:00Z",
      "onboarding_master_completed_at": "2026-01-11T10:00:00Z",
      "onboarding_personal_completed_at": "2026-01-11T11:00:00Z",
      "tariff_plan": "pro",
      "clients_count": 42,
      "last_activity_at": "2026-01-20T09:30:00Z"
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

`last_activity_at` может быть `null`, если у специалиста нет записей активности в `MessageLog`.

### Data model impact

- Новые таблицы не требуются.
- `clients_count` вычисляется агрегированием по таблице `Client` (количество клиентов на специалиста).
- `last_activity_at` вычисляется как `MAX(created_at)`/аналогичный timestamp из таблицы `MessageLog` по специалисту.
- Для MVP допускается runtime-агрегация; оптимизации (материализованные представления/кэш) вне scope этой US.

---

## UX

### Screen structure

- Заголовок: «Специалисты».
- Панель фильтров: `status`, `tariff_plan`, `active_since_hours`.
- Таблица со столбцами:
  - Specialist ID
  - Public Name
  - Status
  - Tariff Plan
  - Clients Count
  - Created At
  - Onboarding Master Completed At
  - Onboarding Personal Completed At
  - Last Activity At
- Пагинация на основе `limit`/`offset`.

### States (loading / empty / error)

- **Loading:** скелетон/индикатор загрузки таблицы и блокировка повторных запросов.
- **Empty:** сообщение «Специалисты не найдены» и подсказка сбросить фильтры.
- **Error:** сообщение об ошибке загрузки + кнопка «Повторить».

---

## Security

### Access control

- Доступ только с заголовком `X-API-Key`.
- Иные механизмы авторизации для этой US не добавляются.

### Sensitive data

- Не возвращать секреты/чувствительные поля.
- Не возвращать телефон/почту Telegram-профиля (если такие поля появятся в будущем).
- Не логировать значения секретов в диагностике и приложении.

### Threat model

- Основной риск: утечка персональных/контактных данных через admin endpoint.
- Митигируется ограниченным набором полей ответа и доступом только через `X-API-Key`.
- Rate-limiting для endpoint находится вне scope US-AD-2.

---

## Tests

### Unit tests

- Проверка валидации query params (`limit`, `offset`, `active_since_hours`).
- Проверка корректной сборки фильтров (`status`, `tariff_plan`, `active_since_hours`).
- Проверка маппинга `last_activity_at = null` при отсутствии активности.

### Integration tests

- Авторизация: endpoint недоступен без валидного `X-API-Key`.
- Корректность агрегации:
  - `clients_count` считается по данным `Client`.
  - `last_activity_at` выбирается как последняя активность из `MessageLog`.
- Проверка пагинации (`limit`/`offset`) и базовой фильтрации.

---

## Documentation updates required

- Добавить US-AD-2 в `docs/40_admin_console/README.md` как planned/backlog.
- При реализации endpoint обновить API-описание Admin Console (если ведётся отдельно).

---

## Implementation notes (current state)

Текущее backend-исполнение endpoint `GET /admin/specialists` реализовано в MVP-варианте со следующими параметрами и полями:

- Query params: `limit`, `offset`, `status`.
- Response item fields:
  - `specialist_id`
  - `public_name`
  - `status`
  - `created_at`
  - `tariff_plan`
  - `clients_count`
  - `last_activity_at` (nullable)

Поля `onboarding_master_completed_at` и `onboarding_personal_completed_at`, а также фильтры `tariff_plan` и `active_since_hours` остаются следующими итерациями US-AD-2.

---

## Security review outcome

- **Data classification:** endpoint возвращает только operational metadata; секреты, токены и приватные тела сообщений не входят в контракт ответа.
- **Anti-enumeration:** admin endpoint-ы не публикуются наружу; входная точка `/admin` скрывается через `404` при неуспешной авторизации; API endpoint-ы требуют `X-API-Key`.
- **Logging:** значения API-ключей (`X-API-Key` / `ADMIN_API_KEY`) не должны попадать в логи приложения, прокси и диагностических инструментов.
- **Future risks:** при добавлении PII-полей (например, phone/email) требуется отдельная ревизия безопасности, явное редактирование чувствительных данных и минимизация экспозиции полей в ответе.
