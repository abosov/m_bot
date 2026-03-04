# US-AD-7 — Admin Actions: Specialist Management

Status: Planned

## User Story

Как `super_admin`  
Я хочу выполнять административные действия над конкретным специалистом из Admin Console  
Чтобы оперативно управлять доступом, интеграциями и тарифом без ручных изменений в базе

## Scope

### Included (MVP)

- Disable specialist.
- Enable specialist.
- Reset OAuth.
- Change tariff plan.
- Запись каждого действия в `admin_audit_log`.

### Excluded (MVP)

- Resync calendar (перенесено в backlog до появления безопасной job-trigger инфраструктуры).
- Массовые действия (bulk operations).
- Редактирование персональных данных специалиста.
- Просмотр audit log UI (`GET /admin/ui/audit-log`) — endpoint и экран планируются в US-AD-8.

## Acceptance Criteria (MVP)

- На странице Specialist Detail доступна панель **Admin Actions** с 4 действиями: disable, enable, reset OAuth, change tariff.
- Для каждого действия используется отдельный POST endpoint в `/admin/ui/specialists/{id}/*`.
- Все POST действия требуют валидной admin cookie-сессии и CSRF token.
- Для неавторизованных/невалидных admin cookie запросов возвращается `404` (anti-enumeration policy).
- `Disable specialist` переводит специалиста в неактивный статус и блокирует дальнейшие рабочие операции специалиста по текущей доменной политике (в текущей реализации используется `specialist.status = suspended`, во внешнем API возвращается `status=disabled`).
- `Enable specialist` возвращает специалиста в активный статус.
- `Reset OAuth` инвалидирует текущую OAuth-связку специалиста (без раскрытия токенов в ответе/логах) и требует повторного подключения.
- `Change tariff plan` обновляет тариф на одно из разрешённых значений бизнес-справочника.
- Каждый успешный и неуспешный admin action пишет запись в `admin_audit_log` с actor, target, action, status и timestamp.
- API-ответы не содержат секретов (tokens, API keys, encrypted payloads).

## Architecture (endpoints + auth + csrf + audit log)

### UI Endpoints (cookie auth)

- `POST /admin/ui/specialists/{id}/disable`
- `POST /admin/ui/specialists/{id}/enable`
- `POST /admin/ui/specialists/{id}/reset-oauth`
- `POST /admin/ui/specialists/{id}/tariff`

Disable endpoint contract (MVP):

- `POST /admin/ui/specialists/{id}/disable`
  - Success response: `{"ok": true, "specialist_id": "<uuid>", "status": "disabled"}`.
  - If specialist not found: `404`.
  - If specialist already disabled: `200` (idempotent).
  - If `is_system=true`: `403` + audit entry with `success=false`, `error_code="FORBIDDEN_SYSTEM"`.


Enable endpoint contract (MVP):

- `POST /admin/ui/specialists/{id}/enable`
  - Success response: `{"ok": true, "specialist_id": "<uuid>", "status": "active"}`.
  - If specialist not found: `404`.
  - If specialist status is `suspended`: move to `active`.
  - If specialist is already `active`: `200` (idempotent).
  - MVP policy choice: `enable` is allowed for system accounts (`is_system=true`), while `disable` stays forbidden for system accounts.


Reset OAuth endpoint contract (MVP):

- `POST /admin/ui/specialists/{id}/reset-oauth`
  - Success response: `{"ok": true, "specialist_id": "<uuid>", "oauth_connected": false}`.
  - If specialist not found: `404`.
  - Deletes OAuth binding row(s) in `google_oauth` by `specialist_id`.
  - `payload.deleted_rows` stores number of removed OAuth rows in `admin_audit_log`.
  - For `is_system=true`: `403` + audit entry with `success=false`, `error_code="FORBIDDEN_SYSTEM"`.
  - Calendar selection is intentionally kept for MVP; only OAuth connectivity is reset, and specialist must reconnect OAuth.


Tariff endpoint contract (MVP):

- `POST /admin/ui/specialists/{id}/tariff`
  - Request JSON: `{"tariff_plan": "<string>"}`.
  - Success response: `{"ok": true, "specialist_id": "<uuid>", "tariff_plan": "<plan>"}`.
  - If specialist not found: `404`.
  - `tariff_plan` must be validated against backend source-of-truth enum `TariffPlan`.
  - Invalid plan: `422` + audit entry with `success=false`, `error_code="VALIDATION"`.
  - For `is_system=true`: `403` + audit entry with `success=false`, `error_code="FORBIDDEN_SYSTEM"`.

`POST /admin/ui/specialists/{id}/tariff` принимает безопасный payload, например:

```json
{
  "tariff_plan": "pro"
}
```

### AuthN/AuthZ

- Endpoint-ы доступны только для роли `super_admin` в Admin Console.
- Используется cookie-based admin session (`admin_session`).
- При отсутствии/невалидности сессии ответ `404`.
- При недостатке прав (роль != `super_admin`) — также `404` согласно anti-enumeration политике admin UI.

### CSRF (exact contract)

Для всех UI POST endpoint-ов применяется double-submit cookie pattern:

1. При рендере admin UI сервер выставляет cookie `admin_csrf` (SameSite=Strict, Secure, HttpOnly=false).
2. UI отправляет значение CSRF токена **только** в заголовке `X-CSRF-Token`.
3. Сервер валидирует:
   - наличие `admin_session`;
   - наличие `admin_csrf` cookie;
   - совпадение token из cookie и token из `X-CSRF-Token`.
4. При провале CSRF проверки возвращается `403` без деталей о внутренней валидации.

### Audit log write-path

Каждый вызов admin action пишет запись в `admin_audit_log`:

- `actor_admin_id` (кто выполнил действие);
- `target_type = specialist`;
- `target_id = {id}`;
- `action` (`disable_specialist`, `enable_specialist`, `reset_oauth`, `change_tariff`);
- `result` (`success` | `rejected` | `error`);
- `reason` (optional, например validation error);
- `request_id`/trace id;
- `created_at` (UTC).

`GET /admin/ui/audit-log` фиксируется как backlog-объём US-AD-8; в US-AD-7 реализуется только запись.

## Data model impact

### `admin_audit_log`

Добавить (или переиспользовать при наличии) поля, достаточные для forensic-аудита admin действий:

- `id`
- `actor_admin_id`
- `target_type`
- `target_id`
- `action`
- `result`
- `reason` (nullable)
- `metadata_json` (nullable, без секретов)
- `request_id` (nullable)
- `created_at`

### Specialist status/tariff fields

- Для disable/enable использовать существующее поле статуса специалиста (`specialist.status`) с доменными значениями, например `active` / `disabled`.
- Для смены тарифа использовать существующее поле `specialist_profile.tariff_plan` (enum `TariffPlan`).
- Дополнительные поля добавляются только при явной необходимости в реализации (например `disabled_at`, `disabled_by`), но не являются обязательными для MVP-спеки.

## UX (Specialist Detail: “Admin Actions” panel + confirmation)

На странице `US-AD-5 Specialist Detail` добавляется панель **Admin Actions**:

- Кнопки: `Disable`, `Enable`, `Reset OAuth`.
- Для `Change tariff` — select + кнопка подтверждения.
- Действия, которые неактуальны в текущем состоянии (например `Enable` для уже active), отображаются disabled.

Паттерн подтверждения:

- Перед выполнением каждого действия показывается confirmation modal.
- Modal содержит:
  - чёткое описание эффекта действия;
  - идентификатор специалиста;
  - предупреждение о записи в audit log;
  - кнопки `Confirm` / `Cancel`.
- После успеха UI показывает toast `Action completed` и перезагружает detail data.
- После ошибки UI показывает безопасное сообщение без раскрытия внутренних деталей.

## Security

- CSRF обязателен для всех UI POST действий (см. контракт выше).
- Для unauth/unauthorized в admin UI сохраняется anti-enumeration ответ `404`.
- Все действия протоколируются в `admin_audit_log`.
- Секреты не возвращаются и не логируются (OAuth tokens, API keys, session values, raw credentials).
- Валидация входных данных обязательна, особенно для `tariff_plan` (allowlist значений).
- Rate limiting для admin actions фиксируется как backlog hardening (вне MVP, но отмечено для последующих US).

## Tests (unit/integration)

### Unit

- Проверка use-case `DisableSpecialist` (корректный статус-переход + audit write).
- Проверка use-case `EnableSpecialist` (обратный статус-переход + audit write).
- Проверка use-case `ResetSpecialistOAuth` (инвалидация OAuth state + audit write, без секретов в output).
- Проверка use-case `ChangeSpecialistTariff` (валидация allowlist + update + audit write).
- CSRF validator: позитивный сценарий и основные negative cases (нет cookie, нет header/field, mismatch).

### Integration

- `POST /admin/ui/specialists/{id}/disable` с валидной cookie+csrf -> success.
- `POST /admin/ui/specialists/{id}/enable` с валидной cookie+csrf -> success.
- `POST /admin/ui/specialists/{id}/reset-oauth` с валидной cookie+csrf -> success.
- `POST /admin/ui/specialists/{id}/tariff` с валидной cookie+csrf и валидным plan -> success.
- Любой endpoint без admin cookie -> `404`.
- Любой endpoint с невалидным/missing CSRF -> `403`.
- Проверка факта записи в `admin_audit_log` для success/error сценариев.

## Definition of Done

- Документ US-AD-7 согласован между архитектурой, backend, security и QA.
- Зафиксированы endpoint-контракты и CSRF-механика для всех MVP действий.
- Определён обязательный формат audit-записи для admin actions.
- Обновлена документация Admin Console (`README` + US-AD-7 spec).
- Подготовлен backlog-линк на US-AD-8 для чтения audit log и на future hardening (rate limit, resync calendar).


## Security review outcome

- UI POST endpoints требуют обязательный CSRF (`admin_csrf` cookie + `X-CSRF-Token`).
- Cookie-auth для admin UI enforced; unauth/invalid session requests возвращают `404` (anti-enumeration).
- System accounts защищены: destructive actions запрещены политикой (`403` с audit записью).
- `admin_audit_log` используется как immutable forensic trail и фиксирует both success/failure outcomes.
- Секреты не возвращаются в API-ответах и не должны попадать в application logs/audit payload.
- Backlog hardening: Nginx Basic Auth для `/admin/*` + rate limit на admin login (US-AD-9).

