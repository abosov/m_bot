# US-AD-13 — Очистка тестового специалиста без удаления specialist

Status: Planned

## Роль

Системный архитектор + архитектор данных + UX дизайнер.

## Архитектурный анализ

### Контекст

Для тестовых сценариев нужен безопасный «сброс данных» специалиста, при котором:

- сама запись `specialist` сохраняется;
- удаляются рабочие данные клиентов/записей, чтобы вернуть аккаунт в «чистое» состояние;
- не ломаются каналы авторизации и профильные настройки, чтобы тестовый специалист мог продолжать использовать аккаунт после reset.

Это функциональный аналог «очистить тестовый контур специалиста», но **без destructive удаления identity**.

### Главный инвариант

Операция доступна только для `is_test=true`, где `is_test` определяется server-side по каноническому `test accounts registry` (US-AD-10).

Если `is_test=false`, операция всегда отклоняется.

---

## User Story

Как `super_admin`  
Я хочу очистить данные тестового специалиста без удаления его аккаунта  
Чтобы быстро переиспользовать тестового специалиста для нового цикла проверки.

---

## Scope операции (архитектурно корректный)

### Included (MVP)

- Сохранение root-identity специалиста (`specialist` не удаляется).
- Удаление всех appointments специалиста и зависимых appointment-данных.
- Удаление client-specialist связей для этого specialist.
- Удаление клиентов, которые остались без других specialist-связей (non-shared clients).
- Удаление reminder/outbox/notification сущностей, завязанных на удаляемые appointments/clients.
- Dry-run preview + execute с подтверждением.
- Audit trail по шагам операции.

### Explicitly preserved (must NOT be touched)

- `specialist` root row.
- `specialist_profile` (owner profile сохраняется).
- `specialist_auth_telegram` / bot identity.
- `google_oauth` и calendar integration settings/state.
- `telegram_bot` настройки, не привязанные к appointments/clients.

### Excluded (MVP)

- Очистка медиаконтента профиля (аватар/публичные блоки), если он не связан с appointments/clients.
- Массовая очистка нескольких специалистов одной операцией (покрывается отдельными US).

---

## Что удаляется (data scope)

Удаляются только runtime-данные тестовой работы специалиста:

1. `appointments` специалиста.
2. Appointment-dependent entities:
   - reminders,
   - confirmation rows,
   - notification log/outbox events, где `entity_ref` указывает на удаляемые appointments,
   - любые denorm/aux записи по appointment id.
3. `client` связи специалиста.
4. `clients` без других активных specialist-связей.
5. Client-dependent reminders/notifications, если они принадлежат удаляемым clients.

Не удаляются сущности identity/config слоя специалиста.

---

## Endpoint contract (proposal)

### 1) Preflight

`POST /admin/ui/specialists/{id}/reset-test-data/preflight`

Response:

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "is_test": true,
  "eligible": true,
  "counts": {
    "appointments": 24,
    "appointment_children": 52,
    "clients_to_detach": 12,
    "clients_to_delete": 9,
    "outbox_notifications_to_delete": 17
  },
  "preserved": [
    "specialist",
    "specialist_profile",
    "specialist_auth_telegram",
    "google_oauth",
    "calendar_settings"
  ],
  "confirmation_token": "opaque-short-lived-token",
  "expires_in_sec": 300,
  "confirmation_phrase": "RESET TEST DATA uuid"
}
```

### 2) Execute

`POST /admin/ui/specialists/{id}/reset-test-data/execute`

Request:

```json
{
  "confirmation_token": "...",
  "confirmation_phrase": "RESET TEST DATA uuid"
}
```

Success response:

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "status": "reset_completed",
  "deleted": {
    "appointments": 24,
    "clients": 9,
    "relations": 12,
    "dependent_rows": 69
  }
}
```

Errors:

- `403 FORBIDDEN_NOT_TEST`
- `403 FORBIDDEN_SYSTEM` (если `is_system=true`, операция блокируется)
- `409 PRECONDITION_FAILED` (stale/expired token)
- `422 VALIDATION` (phrase mismatch)

---

## Строгий порядок очистки (DB)

1. Appointment-dependent children (reminder/confirmation/outbox/notification refs).
2. Appointments.
3. Client-dependent children (если есть отдельные таблицы ссылок/уведомлений).
4. Specialist-client relation rows.
5. Clients without remaining relations.

Причина: сначала удалить самые зависимые записи, затем родительские.

---

## Транзакционность и post-commit

### Транзакционно (single DB transaction)

- Повторная проверка eligibility: `is_test=true`, `is_system=false`.
- Валидация confirmation token + phrase.
- DB-cleanup по строгому порядку.
- Запись audit результата DB-фазы.

Если ошибка внутри DB-фазы -> полный rollback.

### Post-commit

В MVP post-commit cleanup минимален, т.к. операция не трогает профильные uploads специалиста.

Допустимы post-commit задачи:

- очистка вторичных кэшей/read-model projections;
- cleanup orphan outbox links, если они не могут быть удалены в той же транзакции.

Post-commit шаги должны быть idempotent и retryable.

---

## Защита от затрагивания боевых данных

Обязательные guardrails:

1. Только test specialists по registry.
2. Запрет для `is_system=true`.
3. Двухфазная схема: preflight + execute.
4. Одноразовый token с коротким TTL.
5. Явная confirmation phrase.
6. Execute использует server-side актуальную проверку, а не только preflight snapshot.

---

## UX (UI-текст и предупреждение)

### Название действия

`Reset test specialist data`

### Warning text (в модалке)

- RU: `Будут удалены все клиенты, записи и связанные уведомления этого тестового специалиста. Аккаунт специалиста, профиль и OAuth/календарь останутся.`
- RU: `Операция необратима для удаляемых данных.`

### Confirmation UI

- Показать summary counts из preflight.
- Отдельный блок `Сохраняется:` со списком preserved сущностей.
- Поле ручного ввода: `RESET TEST DATA <specialist_id>`.
- Кнопка execute активна только при валидной phrase + checkbox «Подтверждаю».

### Result UI

- Success toast: `Test data reset completed`.
- Detail panel: фактические deleted counters.
- Partial/error: безопасное сообщение + reference на audit/request id.

---

## Audit trail

События:

- `reset_test_data_preflight_requested`
- `reset_test_data_execute_requested`
- `reset_test_data_committed`
- `reset_test_data_rolled_back`

Поля:

- actor_admin_id
- target_specialist_id
- target_flags (`is_test`, `is_system`)
- deleted_counts
- preserved_scope
- outcome/error_code
- request_id/trace_id
- timestamp UTC

---

## Error / partial semantics

- DB-phase fail => `rolled_back`, данных не удалено.
- Если post-commit cache cleanup fail => `completed_with_warnings`, бизнес-данные уже очищены.
- Повтор execute после успешного reset должен быть идемпотентным (`nothing_to_delete` как успешный исход).

---

## Security impact

- Операция ограничена admin auth + CSRF + anti-enumeration policy.
- Уменьшение риска «удалили аккаунт по ошибке»: specialist identity не удаляется в этом сценарии.
- Защита от misuse через строгую проверку test-only eligibility.

---

## Data impact

- Новые бизнес-флаги в `specialist` не добавляются.
- Возможно использование ephemeral confirmation token storage (TTL).
- Потенциально потребуется расширение mapping таблиц для корректной очистки notification/outbox зависимостей.

---

## Tests required

### Unit

- Eligibility validator (`is_test=true`, `is_system=false`).
- Deletion planner order validation.
- Token/phrase validation.
- Shared client rule (delete relation vs delete client).
- Idempotent re-run (`nothing_to_delete`).

### Integration

- Happy path reset: specialist/profile/oauth/bot/calendar сохранены, runtime data удалены.
- Non-test specialist reset attempt -> `403 FORBIDDEN_NOT_TEST`.
- System specialist reset attempt -> `403 FORBIDDEN_SYSTEM`.
- Mid-transaction DB error -> rollback.
- Outbox/notification dependent cleanup correctness.

### UI

- Preflight counters and preserved list rendered correctly.
- Warning texts and confirmation phrase gate execute button.
- Result panel shows deleted counters.

---

## Documentation required

- Добавить US-AD-13 в `docs/40_admin_console/README.md`.
- При реализации обновить runbook по безопасному reset тестовых аккаунтов.

---

## Definition of Done

- Создана спецификация US-AD-13.
- Архитектурно зафиксирован корректный scope: очищаем runtime-данные, сохраняем specialist identity/profile/oauth.
- Определены UI warning/confirmation, guardrails и audit semantics.
