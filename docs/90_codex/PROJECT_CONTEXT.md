# PROJECT CONTEXT

## 1) Purpose of Zumbot
Zumbot is a booking and specialist-management platform with Telegram bot support and web surfaces for public discovery and specialist self-service.

Primary user roles:
- Client: discovers specialists and books services.
- Specialist: manages profile data and availability.
- Admin/Operations: oversees catalog quality, safety, and destructive maintenance actions.

Key product scenario:
- A client discovers a specialist (public page), books a slot, receives updates via bot/web flows, while specialists and admins maintain accurate operational data.

## 2) System Boundaries
Inside the system:
- Backend APIs, service logic, ORM/data access, SQL migrations.
- Telegram bot handlers and dispatchers.
- Frontend/web pages for public and specialist/admin-facing interactions.
- Operational scripts and tests.

Outside the system:
- External messaging and identity providers.
- Third-party integrations (calendar/payment/notification providers).
- Deployment platform infrastructure.

Responsibility zones:
- Product/runtime logic belongs to backend/services/handlers/frontend.
- Schema ownership belongs to SQL migrations.
- Process/guardrails ownership belongs to docs/90_codex.

## 3) Architectural Layers
- API layer: request/response transport, validation, and routing boundaries.
- Service layer: business rules and orchestration.
- ORM models: persistence mapping that mirrors schema.
- SQL migrations: authoritative schema evolution and DB defaults.
- Frontend/UI: public and authenticated user interaction surfaces.
- Infrastructure: deployment/runtime environment, network, and platform concerns.

## 4) Source of Truth
- Schema source of truth: SQL migrations.
- ORM mirrors schema and must not define `server_default`.
- Endpoints must be registered through routers.
- Engineering process source: `docs/90_codex/CODEX_OPERATING_SYSTEM.md`.

API boundary types:
- Public API: externally consumable endpoints (e.g., public specialist pages/data).
- Private API: authenticated specialist workflows and profile operations.
- Admin API: elevated operational endpoints, especially destructive actions with audit logging.

## 5) Core Runtime Flows
Regression-critical runtime flows include:
- Onboarding flow.
- Booking flow.
- Telegram bot interaction flows.
- Public specialist page retrieval/display flow.
- Admin console operational flow.

## 6) Security / Safety Boundaries
- OAuth scopes must not be expanded without explicit architecture/security decision.
- Destructive admin operations require audit logging.
- Secrets must not appear in documentation, examples, or logs.

## 7) Regression-Critical Areas
The following areas must not break during feature delivery:
- Specialist discovery and public profile rendering.
- Booking creation and state transitions.
- Specialist profile private update workflows.
- Telegram bot dispatch and interaction routing.
- Admin destructive operation control and auditability.

## 8) What Usually Changes vs What Must Be Stable
Usually changes (local feature scope):
- Endpoint payload fields, UI copy/layout, service-level feature flags, local business rules.

Must remain stable (architecture scope):
- Layer boundaries and routing ownership.
- SQL migrations as schema source of truth.
- ORM prohibition on `server_default`.
- Security boundaries (OAuth scope and admin audit requirements).

## 9) How to Use This Document in Prompts
For non-trivial implementation prompts, reference:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/PROJECT_CONTEXT.md`

## 10) Repository Entry Points

Common implementation entry points:

- backend/api/ — HTTP routers
- backend/services/ — domain/business logic
- backend/models/ — ORM models
- migrations/ or database/migrations/ — schema evolution
- frontend/ — UI surfaces
- tests/ and backend/tests/ — automated test suites
- docs/ — architecture and process documentation
