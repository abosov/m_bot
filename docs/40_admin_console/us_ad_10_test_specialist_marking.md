# US-AD-10 — Test specialist identification in Admin Console

Status: Implemented (marker + visibility)

## Архитектурный анализ

### Контекст и целевое поведение

US-AD-10 вводит явную классификацию тестовых специалистов на уровне основной модели специалиста. История покрывает источник истины в БД, видимость маркера в admin API/UI и фильтрацию.

Ключевой операционный сценарий: маркировка и фильтрация test-аккаунтов как базовый слой для последующих admin-safe workflow.

### Архитектурные решения (фиксированные)

1. В модель `specialist` добавляется флаг:

   - `is_test BOOLEAN NOT NULL DEFAULT FALSE`

2. Для запрета некорректного состояния добавляется инвариант:

   - `CHECK NOT (is_system AND is_test)`

3. Изменение `is_test=true` разрешено только:

   - admin workflow (приватный admin-контур);
   - миграции/скрипты сопровождения данных.

4. Маркер `is_test` используется как входной сигнал для последующих destructive guard-правил в US-AD-11/12/13.

5. Admin UI обязан явно маркировать тестовых специалистов (`TEST` badge).

### Слой данных

- Миграция схемы добавляет колонку `specialist.is_test` с `NOT NULL DEFAULT FALSE`.
- Миграция также добавляет `CHECK NOT (is_system AND is_test)`.
- На существующих данных выполняется backfill `NULL -> FALSE` в рамках миграции.
- Все новые записи `specialist` получают `is_test=false`, если флаг не установлен в разрешённом admin-потоке.

### Слой API

- `admin` API включает поле `is_test` в DTO специалиста (включая `GET /admin/ui/specialists`).
- Production/public API не принимает и не изменяет `is_test` (поле исключено из input-моделей и update-handlers).
- Любые попытки изменения `is_test` вне admin-контура трактуются как нарушение контракта API (валидационная ошибка/игнорирование поля по текущему стандарту сервиса).

### Слой бизнес-логики и прав доступа

- Установка `is_test=true` доступна только при наличии admin-прав и только через явно выделенные admin use-cases.
- Для system-аккаунтов попытка установить `is_test=true` должна отклоняться на двух уровнях:
  - приложение: domain validation;
  - БД: `CHECK`-constraint как защита целостности.
- Проверки destructive guard-условий реализуются в follow-up историях (US-AD-11/12/13).

### Слой UI (Admin Console)

- В таблице специалистов отображается заметный, но нейтральный badge `TEST`.
- Маркировка `TEST` должна быть независимой от `SYSTEM` и не скрывать системный статус.
- В списках/деталях, где доступны destructive операции, статус `TEST` должен быть визуально очевиден до подтверждения действия.

### Наблюдаемость и аудит

- Изменения `is_test` должны попадать в audit log admin-действий (`actor`, `target_specialist_id`, old/new `is_test`, timestamp).
- Логирование policy denials по destructive guard относится к follow-up историям (US-AD-11/12/13).

### Какие слои можно и нельзя менять

Можно менять в рамках US-AD-10:

- Admin backend read layer (`/admin/ui/specialists` DTO/serializer) для добавления поля `is_test`.
- Admin UI таблицу специалистов (новый визуальный индикатор/колонка `Test`).
- Документацию и QA-набор тестов для admin-флоу.

Нельзя менять в рамках US-AD-10:

- доменную модель специалиста для клиентского/публичного контуров;
- пользовательские сценарии вне admin-контура;
- бизнес-логику production действий, кроме явной фиксации guardrail-правил для future admin actions на уровне спецификации.

### Влияние на будущие Admin Actions

Политика вперёд:

- destructive/admin-sensitive действия (`disable`, `reset-oauth`, `tariff change`) для `is_test=true` должны выполняться в режиме explicit intent (минимум предупреждение + отдельное подтверждение).
- по умолчанию в списках действий `test` аккаунты не исключаются автоматически, но явно помечаются, чтобы снизить риск операционной ошибки.
- audit log должен фиксировать, что действие выполнено над `is_test=true` аккаунтом (`target_flags: ["test"]`).

---

## User Story

Как `super_admin`  
Я хочу видеть, является ли специалист тестовым, прямо в таблице специалистов Admin Console  
Чтобы корректно интерпретировать метрики и безопасно выполнять административные действия.

## Scope

### Included (MVP)

- Добавление признака `is_test` в response модели списка специалистов (`GET /admin/ui/specialists`).
- Отрисовка в таблице явного индикатора `TEST` (badge/колонка).
- Документирование источника истины: флаг `specialist.is_test` с admin-only управлением.
- Фиксация policy для future admin actions (warning/explicit confirm для test аккаунтов).

### Excluded (MVP)

- Массовое редактирование test-статуса из UI.
- Массовое автоматическое переключение `is_test` вне выделенных admin workflow.
- Изменение Overview-метрик (выносится в отдельную US, если потребуется фильтр `include_test`).

## Acceptance Criteria

- В `specialist` добавлено поле `is_test` (`BOOLEAN NOT NULL DEFAULT FALSE`).
- Невозможно сохранить состояние `is_system=true` и `is_test=true` одновременно.
- Admin API возвращает `is_test` в моделях специалистов.
- Admin UI показывает явный `TEST` badge для `is_test=true`.
- Production/public API не позволяет менять `is_test`.

## API impact

### GET `/admin/ui/specialists`

Расширение ответа:

- `is_test: boolean` — персистентный признак из поля `specialist.is_test`.
- `is_system: boolean` — признак системного аккаунта для безопасной фильтрации и визуальной маркировки.

Минимальный контракт item (добавочные поля допускаются):

```json
{
  "specialist_id": "...",
  "email": "...",
  "is_system": false,
  "is_test": false
}
```

Фильтрация:

- Query param `test_only=1` применяет условие `WHERE is_test = TRUE`.

Совместимость:

- backward-compatible расширение (добавление нового поля без удаления существующих).

## Data impact

- Таблица `specialist` получает поле `is_test BOOLEAN NOT NULL DEFAULT FALSE`.
- Добавляется `CHECK NOT (is_system AND is_test)` для защиты целостности данных.
- Потребуются migration + rollback-стратегия для схемы БД.

## UX impact (таблица специалистов)

Рекомендованный паттерн:

- Колонка `Flags` или `Type` с badge `TEST`.
- Для `is_system=true` отображается `SYSTEM`, для `is_test=true` отображается `TEST`; совместное состояние недопустимо по DB-constraint.
- Badge `TEST` визуально нейтральный (не как error), но заметный.

## Security decision

`is_test` is a safe classification attribute for admin operations.

Security constraints:
- `is_test` must never be user-controlled from public/production API.
- Only admin workflows and migrations may set `is_test=true`.
- Secrets/tokens must never be returned in admin specialists payload.

## Security impact

- Новых PII и секретов не добавляется.
- Anti-enumeration и текущая admin auth-модель не изменяются.
- Признак `is_test` считается операционным metadata-полем и не должен использоваться для обхода авторизации.

Destructive guards based on this marker are specified for follow-up stories (US-AD-11/12/13).

## Tests required

- Migration test: колонка `is_test` и `CHECK NOT (is_system AND is_test)` успешно создаются.
- Unit: попытка выставить `is_test=true` для `is_system=true` блокируется.
- Unit: production/public handlers не принимают изменение `is_test`.
- Integration: `GET /admin/ui/specialists` возвращает `is_test` для смешанной выборки (`normal`, `system`, `test`).
- Integration (follow-up stories): destructive guard behavior is validated in US-AD-11/12/13 test sets.
- UI test: таблица корректно отображает `TEST` badge и не ломает существующие фильтры/сортировку.

## Documentation required

- Добавить US-AD-10 в `docs/40_admin_console/README.md`.
- При реализации update для runbook/operational docs по процессу маркировки test-аккаунтов.

## Definition of Done

- Создана и согласована архитектурная секция по US-AD-10 с явным контрактом `is_test`.
- Зафиксированы ограничения на сочетание `is_system` и `is_test`, а также на изменение `is_test` только через admin/migration.
- Определены API/UX последствия для маркера и фильтрации; destructive guardrails зафиксированы как follow-up (US-AD-11/12/13).


## Data model impact

- Single source of truth for test specialist classification is `specialist.is_test` in the DB schema.
- The schema contract is enforced by migration:
  - `is_test BOOLEAN NOT NULL DEFAULT FALSE`;
  - `CHECK (NOT (is_system = TRUE AND is_test = TRUE))` via `specialist_test_system_exclusive`;
  - index `idx_specialist_is_test` for deterministic filtering in admin flows.
- ORM reflects this as a non-nullable boolean field without ORM-side `server_default` as the source of truth.

## Security notes

- `is_test` is admin-operational metadata and must not be writable from public/production APIs.
- `is_system=true` accounts are explicitly excluded from test classification at DB level by `specialist_test_system_exclusive`.
- Marker semantics are consumed by follow-up destructive workflows (US-AD-11/12/13).

## Operational usage

- Admin specialists payloads must expose `is_test` so operators can reliably identify test accounts.
- Admin actions that can mutate or delete data must use `specialist.is_test` as the deterministic guard input.
- Test data reset and cleanup utilities should treat `specialist.is_test` as canonical account classification when deciding destructive scope.


## UI section

- В таблице специалистов Admin Console в колонке `Flags` отображается badge `TEST` для `is_test=true`.
- Badge `TEST` выполнен в виде небольшого pill-label (amber/orange), чтобы быть заметным, но не доминировать над строкой таблицы.
- Для badge `TEST` добавлен tooltip: `Test specialist. Used for admin test-account workflows.`
- Для `is_system=true` по-прежнему отображается отдельный badge `SYSTEM` с отличающимся нейтральным стилем.
- На странице деталей специалиста в заголовке отображается маркер `TEST ACCOUNT` (и отдельно `SYSTEM ACCOUNT` для системных записей), без изменения основной структуры layout.


## Scope clarification (implementation boundary)

US-AD-10 implementation scope is limited to:
- marker in data model (`specialist.is_test`),
- visibility in admin payloads/UI,
- filtering via `test_only=1`.

Destructive operations and strict destructive guards that consume this marker are part of follow-up stories (US-AD-11 / US-AD-12 / US-AD-13).
US-AD-10 itself does not expand destructive action surface.
