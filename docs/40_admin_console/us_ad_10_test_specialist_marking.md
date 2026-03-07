# US-AD-10 — Test specialist identification in Admin Console

Status: Planned

## Архитектурный анализ

### Контекст и целевое поведение

US-AD-10 вводит явную классификацию тестовых специалистов на уровне основной модели специалиста. Для безопасных destructive admin-операций нужен детерминированный и быстро проверяемый признак, доступный в БД, API и UI.

Ключевой операционный сценарий: массовые/разрушительные admin-действия должны быть разрешены только для тестовых, не-системных аккаунтов.

### Архитектурные решения (фиксированные)

1. В модель `specialist` добавляется флаг:

   - `is_test BOOLEAN NOT NULL DEFAULT FALSE`

2. Для запрета некорректного состояния добавляется инвариант:

   - `CHECK NOT (is_system AND is_test)`

3. Изменение `is_test=true` разрешено только:

   - admin workflow (приватный admin-контур);
   - миграции/скрипты сопровождения данных.

4. Для destructive admin-операций вводится обязательный guard:

   - `is_test = true`;
   - `is_system = false`.

5. Admin UI обязан явно маркировать тестовых специалистов (`TEST` badge).

### Слой данных

- Миграция схемы добавляет колонку `specialist.is_test` с `NOT NULL DEFAULT FALSE`.
- Миграция также добавляет `CHECK NOT (is_system AND is_test)`.
- На существующих данных backfill не требуется, т.к. default безопасно выставляет `false`.
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
- Все destructive операции должны проверять guard-условие до выполнения side effects.

### Слой UI (Admin Console)

- В таблице специалистов отображается заметный, но нейтральный badge `TEST`.
- Маркировка `TEST` должна быть независимой от `SYSTEM` и не скрывать системный статус.
- В списках/деталях, где доступны destructive операции, статус `TEST` должен быть визуально очевиден до подтверждения действия.

### Наблюдаемость и аудит

- Изменения `is_test` должны попадать в audit log admin-действий (`actor`, `target_specialist_id`, old/new `is_test`, timestamp).
- Отклонённые destructive операции из-за guard (`is_test=false` или `is_system=true`) логируются как policy denials.

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

Destructive admin operations must require:

- `is_test=true`
- `is_system=false`

## Tests required

- Migration test: колонка `is_test` и `CHECK NOT (is_system AND is_test)` успешно создаются.
- Unit: попытка выставить `is_test=true` для `is_system=true` блокируется.
- Unit: production/public handlers не принимают изменение `is_test`.
- Integration: `GET /admin/ui/specialists` возвращает `is_test` для смешанной выборки (`normal`, `system`, `test`).
- Integration: destructive admin-операция отклоняется для (`is_test=false` или `is_system=true`) и разрешается только при (`is_test=true` и `is_system=false`).
- UI test: таблица корректно отображает `TEST` badge и не ломает существующие фильтры/сортировку.

## Documentation required

- Добавить US-AD-10 в `docs/40_admin_console/README.md`.
- При реализации update для runbook/operational docs по процессу маркировки test-аккаунтов.

## Definition of Done

- Создана и согласована архитектурная секция по US-AD-10 с явным контрактом `is_test`.
- Зафиксированы ограничения на сочетание `is_system` и `is_test`, а также на изменение `is_test` только через admin/migration.
- Определены API/UX последствия и guardrails для destructive admin-операций.
