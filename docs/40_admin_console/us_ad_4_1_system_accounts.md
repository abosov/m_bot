# US-AD-4.1: System specialists filtering in metrics and list

Status: Implemented

## User Story

Как `super_admin`  
Я хочу, чтобы системные учётки (например master bot) были помечены как `system` и исключались из dashboard по умолчанию,  
Чтобы продуктовые метрики и списки отражали реальных специалистов.

---

## Acceptance Criteria

- Добавлено поле `Specialist.is_system` (default `false`).
- Существующий мастер-бот (`zumhelper_bot`) помечен `is_system=true`.
- Overview-метрики по умолчанию считают только `is_system=false`.
- Specialists list по умолчанию показывает только `is_system=false`.
- Query param `include_system=true` включает системные аккаунты.
- UI: чекбокс **«Показывать системные»** управляет `include_system` и обновляет Overview + таблицу.
- Изменение покрыто тестами.
- Документация обновлена.

---

## Architecture

### DB

- Добавляется поле `specialist.is_system` (`boolean`, default `false`).

### Endpoint changes

- `GET /admin/ui/overview?include_system=0|1`
- `GET /admin/ui/specialists?include_system=0|1`
- (Опционально) те же query-параметры для:
  - `GET /admin/overview?include_system=0|1`
  - `GET /admin/specialists?include_system=0|1`

Поведение по умолчанию (если параметр отсутствует): `include_system=0`.

---

## Data migration rule

- Установить `is_system=true` для специалистов, у которых `specialist_auth_telegram.tg_username == 'zumhelper_bot'`.
- Обоснование: `tg_username` для этого аккаунта — стабильный идентификатор существующей системной учётки в текущей модели данных.
- Для будущих системных аккаунтов правило: при создании/миграции явно выставлять `is_system=true` и документировать идентификатор.

---

## UX

- Добавить чекбокс **«Показывать системные»** рядом с Overview или в панели фильтров Specialists.
- По умолчанию чекбокс выключен.
- Изменение состояния чекбокса обновляет оба источника данных:
  - Overview метрики
  - Specialists таблицу

---

## Security

- Новых PII/секретов не добавляется.
- Anti-enumeration сохраняется: при неавторизованном доступе endpoint-ы возвращают `404`.

---

## Tests

- По умолчанию (`include_system` отсутствует или `false`) системные аккаунты исключаются:
  - из Specialists list,
  - из Overview-метрик.
- При `include_system=true` системные аккаунты включаются:
  - в Specialists list,
  - в Overview-метрики.


---

## Implementation notes

- В `specialist` добавлено поле `is_system` (`boolean`, default `false`).
- Для UI endpoint-ов поддержан query-параметр `include_system`:
  - `GET /admin/ui/overview?include_system=0|1`
  - `GET /admin/ui/specialists?include_system=0|1`
- Поведение по умолчанию: при отсутствии параметра или `include_system=0` системные аккаунты исключаются из Overview и Specialists list.


---

## Security review outcome

- Изменение ограничено фильтрацией данных; новые чувствительные данные не добавляются.
- Исключение system accounts по умолчанию снижает риск случайного раскрытия внутренних системных сущностей в продуктовых метриках и списках.
- Параметр `include_system` доступен только в admin-контуре и защищён текущей cookie-auth моделью для UI endpoint-ов.
- Требуется контролировать, что логи не содержат cookies/tokens (включая admin session и другие auth-данные).
