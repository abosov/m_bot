# US-AD-11 — Безопасное удаление одного тестового специалиста

Status: Designed (System Architect)

## Роль

Системный архитектор + архитектор данных + специалист ИБ.

## Архитектурный анализ

### Контекст

В admin-контуре требуется операция полного удаления тестового специалиста вместе со связанными сущностями.
Операция потенциально разрушительная и необратимая, поэтому должна быть построена как **guarded destructive flow** с многоуровневой защитой:

- техническая защита от удаления production-аккаунта;
- строгий порядок удаления зависимостей;
- предсказуемые транзакционные границы;
- forensics-ready audit logging;
- controlled cleanup файловых артефактов.

### Главный инвариант безопасности

Удаление разрешено **только** при одновременном выполнении условий:

- `is_test=true`;
- `is_system=false`.

`is_test` определяется канонически через `test accounts registry` (US-AD-10), а не через эвристики и не через локальный UI state.

Если специалист не подтверждён как тестовый на сервере в момент выполнения действия — операция должна быть отклонена.

---

## User Story

Как `super_admin`  
Я хочу безопасно удалить одного тестового специалиста через Admin Console вместе со всеми связанными данными  
Чтобы очищать тестовый контур без риска затронуть боевых пользователей.

---

## Scope

### Included (MVP)

- Удаление одного специалиста, подтверждённого как test account.
- Удаление связанных `clients` этого специалиста.
- Удаление `appointments` и связанных сущностей.
- Удаление `specialist_auth_telegram`.
- Удаление `google_oauth`.
- Удаление `telegram_bot`-связанных сущностей специалиста (в границах текущей схемы).
- Удаление `specialist_profile`.
- Удаление public profile storage/медиа и uploads специалиста.
- UI confirmation c explicit intent.
- Audit log для попытки/успеха/ошибки.
- Явная модель rollback/partial failure + post-commit cleanup semantics.

### Excluded (MVP)

- Массовое удаление (bulk delete).
- Самообслуживание удаления не из admin-контура.
- Асинхронное удаление по расписанию (batch reaper).

---

## Data-flow (high level)

1. Admin UI открывает карточку специалиста и инициирует `Delete test specialist`.
2. UI выполняет preflight scan (`dry-run`) и получает:
   - подтверждение eligibility (`is_test=true`, `is_system=false`);
   - счётчики сущностей к удалению;
   - deletion token (одноразовый, короткоживущий).
3. Admin вводит явное подтверждение `DELETE TEST SPECIALIST`.
4. UI отправляет execute-запрос с CSRF + deletion token + confirmation phrase.
5. Backend повторно валидирует guardrails и запускает deletion flow:
   - транзакционный этап DB-delete (строгий порядок);
   - фиксация результата + outbox задач post-commit cleanup.
6. Post-commit worker удаляет файловые артефакты/внешние следы, пишет итоговые cleanup-события в audit.

---

## Endpoint contract (proposal)

`POST /admin/ui/specialists/{id}/delete-test`

Один endpoint обслуживает двухшаговый workflow:

- `mode=preflight` — только сканирование и возврат счётчиков;
- `mode=execute` — подтверждённое удаление в транзакции.

### 1) Preflight (`mode=preflight`)

Request:

```json
{
  "mode": "preflight"
}
```

Response (пример):

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "eligible": true,
  "flags": {
    "is_test": true,
    "is_system": false
  },
  "counts": {
    "clients": 3,
    "appointments": 18,
    "media": 7,
    "oauth_tokens": 1
  },
  "deletion_token": "opaque-short-lived-token",
  "expires_in_sec": 300,
  "confirmation_phrase": "DELETE TEST SPECIALIST"
}
```

### 2) Execute (`mode=execute`)

Request:

```json
{
  "mode": "execute",
  "deletion_token": "...",
  "confirmation_phrase": "DELETE TEST SPECIALIST"
}
```

Success response:

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "db_delete": "committed",
  "cleanup_status": "scheduled"
}
```

Failure classes:

- `403 FORBIDDEN_NOT_TEST` — специалист не test.
- `403 FORBIDDEN_SYSTEM` — системная учётка (`is_system=true`).
- `409 PRECONDITION_FAILED` — token истёк/невалиден, stale preflight.
- `422 VALIDATION` — некорректная phrase.
- `500 INTERNAL` — ошибка удаления (должен быть rollback DB-транзакции).

Auth/security:

- Только admin cookie session + CSRF (как в US-AD-7/US-AD-9).
- Для неавторизованных — `404` (anti-enumeration).

---

## Строгий порядок удаления (DB layer)

Порядок задаётся принципом: сначала самые зависимые записи, затем родительские.

1. `appointment`-related children (reminders, links, logs, confirmations, denorm tables — по фактической схеме).
2. `appointments` специалиста.
3. Сущности, завязанные на specialist-client relation:
   - client-specialist link таблицы;
   - `clients`, принадлежащие только этому specialist-контексту.
4. `google_oauth`.
5. `telegram_bot`-связанные записи специалиста (если есть отдельные таблицы состояния).
6. `specialist_profile` и public profile DB rows.
7. `specialist_auth_telegram`.
8. `specialist` (корневая запись).

Правило для `clients`:

- удалять только клиентов, которые не имеют валидных связей с другими специалистами;
- при наличии shared-связей — удаляется только связь с target specialist, сам client сохраняется.

---

## Транзакционность vs post-commit

### Транзакционно (одна DB transaction)

- Проверка актуального `is_test` по registry snapshot/reference на момент execute.
- Повторная валидация deletion token + confirmation phrase.
- Все DB-delete операции по порядку выше.
- Запись `admin_audit_log` о результате DB-фазы.
- Постановка outbox-события `test_specialist_deleted` для cleanup.

Если любой DB-шаг падает -> **полный rollback** transaction.

### Post-commit (асинхронно, retryable)

- Удаление файлов в public profile storage / uploads (локальные и/или object storage).
- Очистка сиротских файлов (orphan cleanup pass).
- Очистка внешних артефактов, не входящих в транзакцию БД.
- Финальная audit-запись о статусе cleanup (`success`/`partial`/`failed`).

Обоснование: файловые и внешние операции не могут быть атомарно откатаны вместе с DB, поэтому выполняются через idempotent worker и retry policy.

---

## Файловая система и orphan cleanup

### Политика удаления файлов

- В транзакции БД сохраняется список file keys/path prefixes, подлежащих удалению (в payload outbox event).
- Worker удаляет файлы идемпотентно: `delete-if-exists`.
- Ошибка удаления отдельного файла не должна ломать уже committed DB state.

### Orphan cleanup

- После основного cleanup запускается secondary pass:
  - поиск orphan refs (файлы без DB-ссылок по префиксу specialist);
  - удаление найденных orphan.
- Если orphan cleanup не завершился, ставится retry, а в audit фиксируется `cleanup_partial`.

---

## Guardrails (защита от ошибочного удаления боевого специалиста)

Обязательные стоп-факторы перед execute:

1. `is_test=true` только по registry membership.
2. `is_system=false` обязательно (системные учётки не удаляются этим сценарием).
3. Двухфазное подтверждение: preflight token + ручной ввод confirmation phrase.
4. Короткий TTL deletion token (например, 5 минут).
5. Повторная server-side проверка всех preconditions непосредственно перед DB transaction.
6. В audit фиксируется причина отказа (`FORBIDDEN_NOT_TEST`, `FORBIDDEN_SYSTEM`, `TOKEN_EXPIRED`, ...).

Дополнительно (hardening backlog):

- optional dual-control (второй админ для подтверждения особо рискованных операций);
- rate limit на destructive actions.

---

## Audit logging

Логируются минимум следующие события:

- `delete_test_specialist_preflight_requested`;
- `delete_test_specialist_execute_requested`;
- `delete_test_specialist_db_committed` или `delete_test_specialist_db_rolled_back`;
- `delete_test_specialist_cleanup_completed` / `cleanup_partial` / `cleanup_failed`.

Ключевой доменный event для журнала аудита: `admin_test_specialist_deleted` (пишется при успешном commit DB-фазы; в payload включается cleanup status).

Обязательные поля audit:

- actor_admin_id;
- target_specialist_id;
- target_flags (`is_test`, `is_system`);
- outcome;
- reason/error_code;
- counts deleted;
- cleanup stats;
- request_id/trace_id;
- timestamp UTC.

Секреты (tokens/cookies/oauth secrets) в audit не пишутся.

---

## Error / rollback / partial failure semantics

### Семантика ответов

- Если DB transaction не закоммичена: операция считается `failed`, данных не удалено.
- Если DB commit успешен, но cleanup частично упал: операция считается `completed_with_cleanup_issues`.

### Компенсации

- Для post-commit ошибок компенсация = повтор cleanup (retry + dead-letter/manual runbook).
- Обратное восстановление удалённых DB данных не поддерживается (destructive operation), поэтому критично preflight+confirm.

### Observability

- Метрика: `admin_delete_test_specialist_total{result=...}`.
- Метрика retry cleanup: `admin_delete_test_specialist_cleanup_retries_total`.
- Alert при накоплении `cleanup_failed` выше порога.

---

## UX confirmation

UI-модалка должна включать:

- явный warning: «Удаление необратимо»;
- specialist id + ключевые счётчики сущностей;
- поле ручного ввода phrase `DELETE TEST SPECIALIST`;
- отображение, что операция разрешена только для test account;
- чекбокс подтверждения понимания последствий.

Кнопка execute активируется только при валидном phrase + подтверждении.

---

## Security impact

- Усиление защиты destructive action через explicit intent и строгий server-side guardrail.
- Прямая профилактика accidental deletion production-аккаунта.
- Соответствие anti-enumeration политике (`404` для unauth).
- Полный forensic trail через audit + outbox cleanup status.

---

## Data impact

- Новых продуктовых признаков типа `specialist.is_test` не добавляется.
- Возможна служебная таблица/структура для deletion tokens (ephemeral, TTL) либо reuse текущего механизма сессий/nonce.
- Используется outbox-событие для post-commit cleanup.

---

## Tests required

### Unit

- Guardrail validator: запрет execute для `is_test=false`.
- Guardrail validator: запрет execute для `is_system=true`.
- Deletion planner: корректный порядок удаления сущностей.
- Token/phrase validation (ok/expired/mismatch).
- Cleanup worker idempotency (`delete-if-exists`).

### Integration

- Full happy path: preflight -> execute -> DB commit -> cleanup scheduled.
- Attempt delete non-test specialist -> `403 FORBIDDEN_NOT_TEST`.
- DB error mid-transaction -> rollback, specialist остаётся.
- Cleanup error post-commit -> DB state удалён, статус `cleanup_partial`, retry создан.
- Shared client case -> удаляется только relation, client не удаляется.

### Security tests

- No auth -> `404`.
- Missing/invalid CSRF -> `403`.
- Token replay after use/expiry -> `409`.

---

## Documentation required

- Зарегистрировать US-AD-11 в `docs/40_admin_console/README.md`.
- При реализации — обновить runbook по manual cleanup/DLQ для post-commit задач.

---

## Definition of Done

- Создана спецификация US-AD-11 с полной схемой безопасного удаления одного test specialist.
- Зафиксированы строгий порядок удаления, транзакционные границы и post-commit cleanup.
- Формально описана защита от удаления нетестового/боевого специалиста.
- Описаны audit logging, UI-confirmation и поведение при rollback/partial failures.
