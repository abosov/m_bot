# US-AD-14 — Admin Diagnostics / Cleanup Tools

Status: Planned

## Роль

Системный архитектор + UX дизайнер + технический писатель.

## Архитектурный анализ

### Контекст

В админ-консоли нужны безопасные диагностические инструменты для оператора:

- находить orphan specialist media;
- находить dev/ops мусор, релевантный серверному окружению;
- запускать read-only проверки из UI с понятным результатом;
- не смешивать диагностику и разрушительные действия.

### Принципиальное ограничение

US-AD-14 — это **только диагностика (read-only)**.

Любая операция, которая меняет данные/файлы/состояние, выводится в отдельные user stories (cleanup/remediation actions) с отдельным security review.

### Почему это важно

- снижает риск случайных разрушительных действий из “удобной” диагностической кнопки;
- делает UX предсказуемым: “scan” ≠ “delete”; 
- упрощает аудит и модель прав доступа.

---

## User Story

Как `super_admin`  
Я хочу запускать безопасные диагностические проверки из Admin Console и видеть структурированный результат  
Чтобы выявлять orphan media и серверный dev/ops мусор без риска повредить production-данные.

---

## Scope

### Included (MVP)

1. **Orphan specialist media diagnostics**
   - проверка консистентности между DB-ссылками и storage-объектами specialist media;
   - выявление orphan объектов и “missing files” ссылок.

2. **Dev/Ops server-relevant clutter diagnostics**
   - проверка наличия нерелевантных/опасных артефактов в серверных директориях (например, временные дампы, debug exports, stray backup files), по allowlist/denylist правилам.

3. **Safe read-only checks from UI**
   - запуск диагностик только в режиме dry-run/read-only;
   - запрет side effects.

4. **Result visualization in Admin Console**
   - summary + детальные находки + severity + рекомендации next steps.

5. **Диагностика vs разрушительные операции**
   - явное визуальное и архитектурное разделение.

### Excluded (MVP)

- Автоматическое удаление найденного мусора/orphan файлов.
- “One-click fix” из этого экрана.
- Запуск shell-команд произвольного вида из UI.

---

## Архитектурные ограничения

### 1) Только заранее зарегистрированные проверки

UI может запускать только предопределённые diagnostics jobs:

- `orphan_specialist_media_scan`
- `server_clutter_scan`

Без пользовательского ввода shell-команд/путей.

### 2) Read-only execution contract

Каждая диагностика обязана:

- не выполнять delete/update/write в БД;
- не удалять и не модифицировать файлы;
- не менять внешние интеграции.

### 3) Изоляция от cleanup действий

Если найдено, что “можно почистить”:

- UI показывает только рекомендацию;
- фактическое remediation запускается в отдельном action-модуле/US с explicit confirmation и отдельным audit-policy.

### 4) Безопасные директории и источники

`server_clutter_scan` проверяет только allowlisted paths, заранее зафиксированные в конфигурации.

Запрещено:

- сканировать произвольные пути по user-input;
- сканировать чувствительные системные области вне утверждённого списка.

### 5) Ограничение объёма и времени

Для стабильности:

- hard timeout на scan job;
- pagination/limit для findings;
- truncation policy для больших результатов.

---

## Data-flow / execution model

1. Admin открывает экран Diagnostics.
2. Нажимает “Run check” для конкретной диагностики.
3. Backend создаёт read-only `admin_diagnostic_job`.
4. Worker выполняет scan по безопасному контракту.
5. Job сохраняет structured findings + summary.
6. UI показывает status/progress/result.

Рекомендованный execution model: async job (даже для read-only), чтобы:

- не блокировать HTTP запрос;
- поддерживать прогресс и историю запусков;
- стандартизировать UX с другими admin jobs.

---

## Endpoint contract (proposal)

### Run diagnostic

`POST /admin/ui/diagnostics/run`

Request:

```json
{
  "check_type": "orphan_specialist_media_scan"
}
```

Allowed `check_type` values (MVP):

- `orphan_specialist_media_scan`
- `server_clutter_scan`

Response:

```json
{
  "ok": true,
  "job_id": "uuid",
  "status": "queued"
}
```

### Get diagnostic result

`GET /admin/ui/diagnostics/jobs/{job_id}`

Response (example):

```json
{
  "job_id": "uuid",
  "check_type": "orphan_specialist_media_scan",
  "status": "completed",
  "summary": {
    "scanned": 1240,
    "findings_total": 18,
    "high": 2,
    "medium": 5,
    "low": 11
  },
  "findings": [
    {
      "severity": "high",
      "code": "ORPHAN_MEDIA_OBJECT",
      "entity_ref": "media://...",
      "message": "Storage object has no DB reference",
      "recommended_action": "Open cleanup workflow US-AD-XX"
    }
  ],
  "read_only": true,
  "started_at": "...",
  "finished_at": "..."
}
```

---

## UX requirements

### Экран

`Admin > Diagnostics`

### Секции

1. **Checks catalog**
   - карточки: “Orphan specialist media”, “Server clutter (dev/ops)”.
   - явный бейдж `Read-only`.

2. **Run history**
   - список запусков: check_type, actor, start time, status, findings count.

3. **Result panel**
   - summary counters;
   - severity breakdown;
   - findings table;
   - рекомендации “что делать дальше” (без кнопок destructive action в MVP).

### UI-тексты/предупреждения

- `Diagnostics are read-only. No data will be modified.`
- `Cleanup actions are not available on this screen.`

### Разграничение диагностики и cleanup

Визуально и терминологически разделить:

- `Run diagnostic` (safe/read-only)
- `Cleanup tools` (disabled link / “available in separate workflow”).

---

## Audit trail

Логируются:

- `admin_diagnostic_run_requested`
- `admin_diagnostic_job_started`
- `admin_diagnostic_job_completed`
- `admin_diagnostic_job_failed`

Поля:

- actor_admin_id
- check_type
- job_id
- status
- summary_counts
- error_code (if any)
- request_id/trace_id
- timestamps UTC

Принцип: findings не должны содержать секреты (tokens, credentials, raw session values).

---

## Security impact

- Минимизация риска через strict read-only contract.
- Исключение command injection: нет произвольных shell input из UI.
- Scope-ограничение сканирования allowlisted paths.
- Anti-enumeration/admin auth политика сохраняется (`404` для unauth).

---

## Data impact

- Нужна служебная сущность `admin_diagnostic_job` (или расширение существующей admin jobs модели).
- Findings хранятся как structured payload (JSON), с лимитами размера.
- Полезно хранить retention policy для истории запусков (например, 30/90 дней).

---

## Error handling

- `failed` статус при timeout/runner error/invalid config.
- Частичный успех для scan допустим:
  - `completed_with_warnings` если часть источников недоступна;
  - UI обязан явно показать coverage limits.
- Повторный запуск разрешён и должен быть идемпотентным в смысле side effects (их нет).

---

## Tests required

### Unit

- Validator `check_type` allowlist.
- Read-only contract guard (no mutating repository calls).
- Findings redaction/sanitization (без секретов).

### Integration

- Run diagnostic -> queued -> completed.
- Invalid check_type -> validation error.
- Large findings -> truncation/pagination policy applied.
- Completed_with_warnings path shown correctly.

### UI

- Read-only badge and warning texts visible.
- Result summary/severity/findings rendering.
- No destructive action buttons on diagnostics screen.

---

## Documentation required

- Добавить US-AD-14 в `docs/40_admin_console/README.md`.
- При реализации обновить runbook с описанием интерпретации findings и дальнейших remediation-процессов.

---

## Definition of Done

- Создана и задокументирована user story US-AD-14.
- Зафиксированы архитектурные ограничения для safe read-only диагностик.
- Определено явное разграничение между “диагностика” и “разрушительные операции”.
