# US-AD-12 — Массовое удаление всех test accounts через Admin Console

Status: Planned

## Роль

Системный архитектор + архитектор данных + UX дизайнер + специалист ИБ.

## Архитектурный анализ

### Контекст

Нужен безопасный UI-аналог CLI-команды:

`zumbot-test-reset --apply --i-know-what-i-am-doing --yes`

Операция высокорисковая (bulk destructive), поэтому её нельзя реализовывать как «один синхронный HTTP delete» без preflight, подтверждений и наблюдаемости.

### Цель

Предоставить управляемую массовую очистку test-контуров (специалисты и связанные данные), исключая риск затронуть production-данные.

### Ключевое решение по исполнению

**Режим выполнения: asynchronous admin job pattern** (job + outbox/task worker), а не synchronous request.

Обоснование:

- объём удаляемых данных может быть большим (timeouts/нестабильность при sync);
- нужен прогресс, промежуточные статусы и повторная обработка ошибок;
- post-commit очистка storage/файлов естественно ложится в job/workflow модель.

---

## User Story

Как `super_admin`  
Я хочу массово удалить все тестовые аккаунты через Admin Console безопасным и контролируемым способом  
Чтобы быстро сбрасывать тестовый контур без риска удаления боевых данных.

---

## Scope операции

### Included (MVP)

- Массовый отбор кандидатов на удаление только среди test accounts.
- Dry-run preview с подсчётом удаляемых сущностей.
- Явное подтверждение операции (multi-step).
- Создание и запуск admin job на удаление.
- Удаление сущностей по каждому test specialist согласно US-AD-11 (single-delete policy).
- Агрегированный результат в UI: success/failed/partial + подробная статистика.
- Полный audit trail: запуск, прогресс, завершение, ошибки.

### Excluded (MVP)

- Удаление non-test аккаунтов в этом же job.
- Автоматический запуск по cron без явной admin-инициации.
- Редактирование registry из этого экрана.

---

## Критерии отбора test accounts

Единственный source-of-truth: `test accounts registry` (как зафиксировано в US-AD-10).

Кандидат попадает в bulk-delete, если одновременно:

1. `is_test=true` по registry membership (server-side).
2. `is_system=false` (системные учётки исключены).
3. Не находится в denylist исключений (например, временно защищённый тестовый аккаунт для QA smoke).

Примечания:

- эвристики по username/email не используются;
- UI список кандидатов строится из server-side snapshot, а не из клиентских фильтров.

---

## Dry-run preview

Перед apply обязателен preflight endpoint:

`POST /admin/ui/test-reset/preflight`

Возвращает:

- `snapshot_id` (immutable идентификатор расчёта);
- список кандидатов (`specialist_id`, display-name, flags);
- агрегированные счётчики по удалению:
  - specialists,
  - clients,
  - appointments,
  - oauth/profile/auth rows,
  - storage objects/uploads (оценка);
- список исключений (например, `is_system=true`, denylist);
- предупреждения о потенциальных рисках;
- `confirmation_token` с TTL.

Dry-run ничего не удаляет.

---

## Подтверждение операции (UX + безопасность)

Apply разрешается только после всех подтверждений:

1. Введена phrase: `DELETE ALL TEST ACCOUNTS`.
2. Подтверждён `snapshot_id` (не stale).
3. Валиден `confirmation_token` (short TTL, one-time use).
4. UI чекбокс «Я понимаю, что операция необратима».

Endpoint:

`POST /admin/ui/test-reset/execute`

Request:

```json
{
  "snapshot_id": "...",
  "confirmation_token": "...",
  "confirmation_phrase": "DELETE ALL TEST ACCOUNTS"
}
```

---

## Что удаляется (data scope)

Для каждого выбранного test specialist применяется тот же безопасный профиль удаления, что в US-AD-11:

- specialist root;
- specialist_auth_telegram;
- specialist_profile и public profile DB rows;
- google_oauth;
- appointments + appointment-related children;
- specialist-client relations и clients (только если не shared);
- telegram bot related records в пределах specialist context;
- uploads/public profile storage объекты (post-commit cleanup).

Важно: shared client не удаляется, если связан с non-deleted specialist.

---

## Data-flow / архитектурная схема

1. Admin запускает preflight.
2. Backend формирует snapshot кандидатов + counts, пишет audit preflight.
3. Admin подтверждает apply.
4. Backend создаёт `admin_job` типа `bulk_delete_test_accounts` со snapshot reference.
5. Worker обрабатывает job батчами:
   - по каждому specialist запускает транзакционное DB-delete (policy US-AD-11);
   - планирует post-commit cleanup для файлов/outbox;
   - фиксирует per-item outcome.
6. Job агрегирует результат, обновляет статус и финальный audit event.
7. UI читает статус/прогресс через polling endpoint.

---

## Synchronous vs async решение

Принято: **только async job**.

Почему sync отклонён:

- риск HTTP timeout;
- нет надёжного механизма resume/retry;
- сложнее безопасно показать partial success и подробные причины ошибок.

---

## Ошибки и partial success

### Модель результата job

- `completed_success` — все кандидаты удалены и cleanup завершён.
- `completed_partial` — часть кандидатов удалена, часть завершилась ошибкой и/или cleanup partial.
- `failed` — критическая ошибка orchestration до meaningful progress.

### Retry стратегия

- Retry per-item для transient DB/storage ошибок (ограниченный backoff).
- Непроходящие кейсы уходят в failed items list + manual runbook.

### Идемпотентность

- Повтор execute с тем же `snapshot_id` после успешного старта не создаёт дублирующий job (возвращает существующий `job_id`).
- Per-specialist delete должен быть idempotent (`already deleted` -> success-like terminal state).

---

## Защита от затрагивания боевых данных

Обязательные guardrails:

1. Server-side filter только по registry test membership.
2. Hard-block `is_system=true`.
3. snapshot-based execution (execute действует только на frozen candidate set).
4. TTL + one-time confirmation token.
5. Confirmation phrase + explicit UI warning.
6. Перед удалением каждого specialist — повторная проверка eligibility (`is_test=true`, `is_system=false`).
7. Audit фиксация каждого skip/reject с reason code.

---

## Audit trail

События:

- `bulk_delete_test_accounts_preflight_requested`
- `bulk_delete_test_accounts_execute_requested`
- `bulk_delete_test_accounts_job_created`
- `bulk_delete_test_accounts_item_deleted`
- `bulk_delete_test_accounts_item_failed`
- `bulk_delete_test_accounts_completed` / `completed_partial` / `failed`

Минимальные поля:

- actor_admin_id
- snapshot_id
- job_id
- totals (planned/deleted/failed/skipped)
- reason/error_code
- request_id/trace_id
- timestamps (UTC)

Секреты и токены в audit не логируются.

---

## UI: как показывать результат

### Экран Bulk Test Reset

Блоки:

1. **Preview**: planned counts + candidate count + exclusions.
2. **Confirmation**: phrase field + irreversible warning + apply button.
3. **Job progress**:
   - статус (`running`, `completed_success`, `completed_partial`, `failed`),
   - прогресс-бар (processed/total),
   - counters: deleted/failed/skipped,
   - ссылка «Показать ошибки» (таблица failed items).
4. **Cleanup status**: storage cleanup success/partial/fail.

### Endpoint-ы для UI

- `POST /admin/ui/test-reset/preflight`
- `POST /admin/ui/test-reset/execute`
- `GET /admin/ui/test-reset/jobs/{job_id}` (progress/result)

---

## Транзакционность и post-commit

### Транзакционно (per specialist)

- DB deletion graph + audit записи DB-фазы.
- outbox enqueue на файловый cleanup.

### Post-commit

- удаление файлов/storage объектов;
- orphan cleanup pass;
- итоговый cleanup status per specialist и aggregate per job.

---

## Security impact

- Усиленная защита destructive bulk операции через multi-step explicit intent.
- Снижение вероятности accidental mass deletion production data.
- Соответствие anti-enumeration: unauth requests получают `404`.
- Форензика через полный audit trail и job-level observability.

---

## Data impact

- Добавляется/используется admin job сущность (`bulk_delete_test_accounts`).
- Добавляется snapshot метаданных preflight (ephemeral, TTL).
- Используется outbox/task для cleanup этапа.

---

## Tests required

### Unit

- Candidate selector: только test && !system && !denylist.
- Snapshot validator: stale snapshot отклоняется.
- Confirmation validator: phrase/token/TTL/one-time-use.
- Result aggregator: корректная модель `success/partial/failed`.

### Integration

- Happy path: preflight -> execute -> job completed_success.
- Защита: non-test аккаунты не попадают в candidate set.
- Защита: system аккаунты всегда excluded.
- Partial path: часть items падает, job = completed_partial.
- Retry path: transient storage error -> retry -> success.
- Execute replay with same snapshot -> тот же job_id / no duplicate job.

### Security

- No auth -> `404`.
- Missing/invalid CSRF -> `403`.
- Invalid token or phrase -> reject.

---

## Documentation required

- Добавить US-AD-12 в `docs/40_admin_console/README.md`.
- При реализации обновить runbook по manual remediation для failed items и cleanup DLQ.

---

## Definition of Done

- Создана спецификация US-AD-12 с безопасной архитектурой массового удаления test accounts.
- Формально определены scope, критерии отбора, dry-run и подтверждение.
- Зафиксированы async job/outbox модель, error/partial-success semantics и UI-result contract.
- Описаны guardrails, предотвращающие затрагивание боевых данных.
