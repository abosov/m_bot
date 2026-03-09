# REPOSITORY MAP

## 1) Purpose
This map gives Codex prompt-time repository injection context so changes land in the correct layer and avoid cross-layer hallucinations.

## 2) High-Level Repository Zones
Current top-level implementation zones:
- `backend/` — API modules, services, schemas, and backend tests.
- `frontend/` — web UI components/pages/styles/utils.
- `docs/` — architecture, ops, API, security, and workflow docs.
- `tests/` — project-level test suites.
- `scripts/` — developer/ops utilities and smoke helpers.
- `migrations/` and `database/migrations/` — SQL schema evolution assets.

## 3) API Zones
- Public API routers: `backend/api/public_specialist.py` (public specialist endpoints).
- Specialist/private API routers: `backend/api/specialist_profile_private.py`.
- Admin API routers: no dedicated admin router module is currently present under `backend/api/`; add admin endpoints as explicit router modules instead of mixing with public/private routes.

Boundary rule:
- Endpoints must be attached through routers and kept separated by audience (public/private/admin).

## 4) Service Layer Zones
Business logic lives primarily under:
- `backend/services/`
- `services/` (integration, billing, telegram-related domain/service logic)

Routers should orchestrate service calls and not hold core business rules.

## 5) Data Layer Zones
- ORM/data mapping: backend data/model code in backend packages.
- SQL migrations: `migrations/sql/` and `database/migrations/`.

Reminder:
- Schema source of truth is SQL migrations.
- ORM must mirror schema and must not define `server_default`.

## 6) Frontend Zones
- Public specialist-facing pages: `frontend/pages/` and related components.
- Specialist profile edit experiences: frontend page/component modules for authenticated specialist workflows.
- Admin UI (if present): docs indicate admin console surfaces under `docs/40_admin_console/`; runtime UI code should remain isolated from public/specialist flows.

## 7) Tests Map
- Unit/integration/backend endpoint tests: `backend/tests/`.
- Project-level tests and cross-cutting suites: `tests/`.
- Add new tests adjacent to the changed layer (API tests near API code, service tests near services, UI tests near frontend test strategy).

## 8) Documentation Map
- User stories: `docs/user-stories/`.
- Architecture: `docs/architecture/`.
- Ops/runbooks: `docs/ops/`, `docs/runbook/`, `docs/36_runbooks/`.
- API docs: `docs/api/`.
- Admin docs: `docs/40_admin_console/`.
- Codex workflow/process docs: `docs/90_codex/`.

## 9) Change Zones Guidance
- Schema change: SQL migration directories first, then ORM alignment and tests/docs.
- Endpoint change: API router modules + schemas/services + endpoint tests.
- Business rule change: service layer first, minimal API/UI adjustments as needed.
- UI change: `frontend/` only (plus relevant docs/tests).
- Docs-only change: `docs/` only.
- Admin destructive operation: admin API/service layer with mandatory audit logging.
- Public page change: public API + frontend public page modules + tests/docs.

## 10) Forbidden Shortcuts
Do not:
- Put business logic in routers.
- Bypass migrations for schema changes.
- Define `server_default` in ORM.
- Modify unrelated layers in a scoped story.

## 11) Prompt Usage Snippet
Before implementation read:
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
