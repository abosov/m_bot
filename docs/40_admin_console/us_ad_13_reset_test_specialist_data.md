# US-AD-13 — Reset test specialist runtime data

Status: Planned

## Role

System Architect

## User Story

As `super_admin`  
I want to reset runtime data for a test specialist  
without deleting specialist identity.

## Goal

Provide a **safe, repeatable reset** for test specialists that removes operational/test traces while preserving the specialist account and configuration needed to continue testing immediately.

---

## Scope

### Delete (runtime data)

1. `clients` of the target specialist.
2. `appointments` of the target specialist.
3. `notifications` tied to deleted appointments/clients/specialist runtime flows.
4. `media` generated as runtime/test artifacts for the specialist (e.g., appointment/client uploads, runtime content blobs).

### Preserve (identity/config)

1. `specialist`.
2. `profile`.
3. `oauth`.
4. `calendar` integration/settings/state.
5. `bot config`.

---

## Guardrails

1. Operation is allowed only for `is_test=true` specialists.
2. Server re-validates eligibility during execute (not only from preflight snapshot).
3. Two-phase flow: **preflight** then **execute**.
4. Short-lived one-time confirmation token.
5. Explicit confirmation phrase (`RESET RUNTIME DATA <specialist_id>`).
6. Full admin audit trail for requested/committed/rolled-back outcomes.

---

## API design

### 1) Preflight

`POST /admin/ui/specialists/{specialist_id}/reset-runtime-data/preflight`

Response:

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "is_test": true,
  "eligible": true,
  "delete_counts": {
    "clients": 12,
    "appointments": 24,
    "notifications": 49,
    "media": 15
  },
  "preserve_scope": [
    "specialist",
    "profile",
    "oauth",
    "calendar",
    "bot_config"
  ],
  "confirmation_token": "opaque-token",
  "expires_in_sec": 300,
  "confirmation_phrase": "RESET RUNTIME DATA <specialist_id>"
}
```

### 2) Execute

`POST /admin/ui/specialists/{specialist_id}/reset-runtime-data/execute`

Request:

```json
{
  "confirmation_token": "opaque-token",
  "confirmation_phrase": "RESET RUNTIME DATA <specialist_id>"
}
```

Success:

```json
{
  "ok": true,
  "specialist_id": "uuid",
  "status": "completed",
  "deleted": {
    "clients": 12,
    "appointments": 24,
    "notifications": 49,
    "media": 15
  },
  "preserved": {
    "specialist": true,
    "profile": true,
    "oauth": true,
    "calendar": true,
    "bot_config": true
  }
}
```

Errors:

- `403 FORBIDDEN_NOT_TEST`
- `409 PRECONDITION_FAILED` (expired/used token)
- `422 VALIDATION` (phrase mismatch)

---

## Deletion order (transactional)

Inside one DB transaction:

1. Delete notification dependencies.
2. Delete appointments.
3. Delete clients.
4. Delete media references/metadata in DB.

Then commit.

After commit (idempotent, retryable):

5. Delete physical media blobs/files by collected keys.

Reasoning: DB consistency first; external file/object storage cleanup should not break transaction atomicity.

---

## Idempotency

- Re-running execute after successful reset is valid and returns `ok=true` with zero deleted counters.
- Missing runtime rows are treated as already-clean state, not as an error.

---

## Audit events

- `reset_runtime_data_preflight_requested`
- `reset_runtime_data_execute_requested`
- `reset_runtime_data_committed`
- `reset_runtime_data_rolled_back`

Audit payload fields:

- actor admin id
- target specialist id
- eligibility flags (`is_test`)
- requested delete counts (preflight)
- actual deleted counts (execute)
- preserved scope
- outcome/error code
- request id / trace id
- UTC timestamp

---

## UX notes

Modal title: `Reset test specialist runtime data`

Warning text:

- `Будут удалены clients, appointments, notifications и media этого тестового специалиста.`
- `specialist, profile, oauth, calendar и bot config будут сохранены.`
- `Операция необратима.`

Controls:

- show preflight counters;
- show explicit preserved list;
- require typed confirmation phrase;
- execute button enabled only when phrase is valid.

---

## Test plan

### Unit

- Eligibility check: only `is_test=true`.
- Deletion planner produces correct buckets (`clients`, `appointments`, `notifications`, `media`).
- Confirmation token + phrase validation.
- Idempotent second run returns zero counters.

### Integration

- Happy path: runtime data deleted; specialist/profile/oauth/calendar/bot config remain.
- Non-test specialist attempt returns `403`.
- DB failure during execute triggers rollback (no partial DB deletion).
- Media blob cleanup failures are reported as post-commit warnings without DB rollback.

### UI

- Preflight counters rendered.
- Preserved scope rendered.
- Confirmation phrase gating works.
- Final result shows actual deleted counters.

---

## Definition of Done

1. Admin API supports preflight + execute for runtime reset.
2. Runtime entities are deleted: clients, appointments, notifications, media.
3. Identity/config entities are preserved: specialist, profile, oauth, calendar, bot config.
4. Audit trail and guardrails are implemented.
5. Idempotency and rollback semantics are covered by tests.
