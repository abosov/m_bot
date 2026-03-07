---
name: zumbot-user-story-workflow
description: Mandatory workflow for all Zumbot engineering tasks, including backend implementation, architectural/user-story/admin-console work, database and migration rules, QA verification design, behavior-impacting documentation updates, infrastructure/deployment rules, and architecture/data-model-impacting refactoring.
---

# Zumbot Development Skill

This skill defines the **mandatory engineering workflow** for implementing features in the Zumbot project.

Use this skill whenever the task involves:

- user stories
- admin console features
- backend/API logic
- database changes
- onboarding flows
- billing/payment logic
- calendar integration
- production deployment behavior
- architectural specifications
- documentation updates

This workflow follows the internal **CODEX Operating System** used in the Zumbot repository.

---

# Mandatory Role Order

All non-trivial tasks must be executed in the following order:

1. **System Architect**
2. **Data Architect**
3. **UX Designer**
4. **Developer**
5. **Technical Writer**
6. **QA Engineer**
7. **Security Reviewer**

Do not skip roles unless the task clearly affects **only documentation or copy text**.

---

# System Architecture Rules

The following principles are **mandatory**.

### Layer boundaries

Respect strict separation between layers:

- API layer
- service layer
- ORM models
- SQL migrations
- infrastructure
- frontend/UI

Changes must occur in the **correct architectural layer**.

The architect must explicitly state:

- which layer is modified
- why this layer is correct
- which layers must NOT be modified

### Infrastructure configuration rules

- Infrastructure changes (Nginx, systemd, VPS configuration) must be minimal and targeted.
- Do not redesign infrastructure unless explicitly requested.
- Update related documentation when infrastructure configuration behavior changes.
- Deliver all infrastructure configuration changes through a pull request.

---

### Database rules

Database schema **must only change via SQL migrations**.

SQL migrations are the **single source of truth** for the database schema **and database-level defaults**.

All database defaults must be defined through SQL migrations.

ORM models must follow migrations and **must not define DB defaults via `server_default`**.

Python-side `default=...` is allowed only for application behavior and **must not replace migration-defined DB defaults**.

Never introduce duplicate schema definitions.

---

### Database Schema Source of Truth

SQL migrations are the **only source of truth** for database schema.

ORM models must **not introduce database defaults**.

Allowed in SQL migrations:

- DEFAULT NOW()
- DEFAULT 0
- DEFAULT TRUE/FALSE
- CHECK constraints
- foreign keys
- indexes

Forbidden in ORM models:

- server_default=...
- implicit DB defaults defined via ORM

Allowed in ORM:

- column types
- nullable flags
- python-side default=...
- relationships

Example

Correct:

SQL migration:

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()

ORM:

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

Incorrect:

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

---


### FastAPI endpoint registration rules

- FastAPI endpoints must always be defined inside routers.
- Routers that define new endpoints must be attached to the application router hierarchy using `include_router()`.
- Every new endpoint must be reachable through the API after implementation.
- Never create endpoint handlers without registering their router.

Common mistake to avoid:

- defining endpoints but forgetting to attach the router.

---

### API Endpoint Registration Rule

Every new API endpoint must be registered in the correct router.

Required steps when creating a new endpoint:

1. Define endpoint function.
2. Register endpoint in the router module.
3. Ensure router is included in the application startup.
4. Add endpoint to API documentation.

Example checklist:

- endpoint function exists
- router decorator exists
- router included in web_server.py
- tests call the endpoint

Example failure (forbidden):

Endpoint defined but router not included.

---

### Tests Required Rule

Every implemented user story must include tests.

Minimum requirements:

- unit tests for core logic
- integration tests for API endpoints
- regression tests if bug fix

Tests must be added in:

tests/

Test naming conventions:

test_<feature>.py

Example:

tests/test_admin_bulk_cleanup_job.py
tests/test_admin_api.py

Checklist for every user story implementation:

- code implemented
- tests added
- tests run successfully

---

### Documentation Synchronization Rule

Every user story implementation must update documentation.

Required documentation updates:

- user story specification file
- API documentation
- architecture documentation if affected

Documentation directory:

docs/

Example files:

docs/40_admin_console/us_ad_12_bulk_delete_test_accounts.md
docs/30_architecture/endpoints.md

Checklist:

- feature implemented
- docs updated
- docs committed in same PR

---

### Security Rule for Admin Operations

Destructive operations must include:

- admin authentication
- CSRF protection
- confirmation phrase
- audit logging

Forbidden patterns:

- destructive endpoints accessible without admin role
- delete operations without audit events
- silent destructive actions

Required audit event example:

admin_test_specialist_deleted
admin_bulk_cleanup_started

---

### Source of truth rules

Avoid duplicate sources of truth.

Examples of forbidden patterns:

- defining DB schema both in ORM and migrations
- storing the same configuration in multiple files
- duplicating logic between API and services

---

# Atomic Prompt Rules

All implementation prompts must be **atomic**.

Each prompt must:

- implement **one logical change**
- be independently executable
- avoid unrelated modifications

Each prompt must start with the format:
US-XXX PROMPT N

Example:
US-AD-12 PROMPT 1

Prompts must contain:

- role responsible for the change
- task description
- files to inspect
- files to modify
- constraints
- acceptance criteria
- documentation updates
- QA checks

---

# Documentation Requirements

Any change affecting behavior must update documentation.

Relevant documentation locations:
docs/
30_architecture/
40_user_flows/
50_ops/
60_api/
70_admin/

Possible documentation updates include:

- architecture diagrams
- API contracts
- admin console capabilities
- operational procedures
- onboarding flows
- deployment procedures

Documentation updates are **not optional**.

---

# UX Requirements

UX must be reviewed when changes affect:

- onboarding flows
- Telegram bot interaction
- public specialist pages
- admin console UI
- booking flows
- payment flows

UX designer must ensure:

- clarity of interaction
- consistent naming
- mobile friendliness
- alignment with Zumbot visual style

---

# QA Requirements

Every feature must define QA checks.

QA must include:

### Functional tests

- happy path
- edge cases
- error handling

### Regression checks

- existing flows must not break
- onboarding must remain functional
- booking flow must remain functional

### Role-based checks

Admin features must verify:

- role permissions
- unauthorized access prevention

---

# Backend QA and Verification Rules

For backend implementation tasks, QA must explicitly verify the backend result against user story and architecture before sign-off.

### Functional verification

- backend behavior matches the user story and approved architecture/design
- expected HTTP/status codes are implemented and tested
- input validation and error handling are correct and explicit

### Database verification

- schema changes are done only through SQL migrations
- migrations apply cleanly in the expected environment
- ORM models match migration-defined schema
- no duplicate schema source of truth is introduced

### Automated tests

- backend changes must include `pytest` coverage where applicable
- new backend behavior must have new/updated automated tests
- regression risks for existing backend flows must be identified and covered

### Integration verification

QA must verify backend changes do not break affected flows, including:

- Telegram bot flows
- public API routes
- onboarding flows
- admin/admin-console flows (when impacted)

### Deployment safety checks

- verify env/config assumptions for the change
- verify startup/deploy compatibility (including migrations/restarts if needed)
- define smoke-check expectations for production-impacting backend changes
- for QA/verification/smoke/diagnostic commands, explicitly specify execution environment: local machine or VPS

### Documentation verification

If backend behavior, API contracts, deployment procedures, admin flows, or architecture changed, related markdown docs must be updated.

### QA output expectations

QA output must explicitly confirm:

- tests passed (or required tests still pending with reason)
- migrations are correct and consistent with ORM
- backend behavior matches approved design
- deployment and smoke-check impact is identified

---

# Security Requirements

Security review is mandatory for:

- admin console features
- payment logic
- OAuth integration
- external API integrations

Security checks must verify:

- authorization boundaries
- audit logging
- least privilege access
- protection of secrets
- no sensitive data leakage

---

# Deployment Rules

Zumbot uses **manual production deployment**.

Auto deployment from CI must not replace manual deployment unless explicitly approved.

All changes that affect production behavior must define:

- migration execution
- service restart
- smoke checks

---

# CLI Command Rules

Whenever CLI commands are provided, the execution environment must be specified.

Examples:
Run locally:
git pull origin main

Run on VPS:
sudo systemctl restart zumbot-backend

Commands must never assume environment implicitly.

---

# Smoke Check Requirements

After deployment the following checks must be performed.

Example smoke checks:

- `/healthz` endpoint
- `/readyz` endpoint
- Telegram bot `getMe`
- service logs via `journalctl`
- database connectivity
- critical API endpoints

---

# OAuth Safety Rules

The Zumbot Google OAuth scopes are restricted.

Allowed scopes:
https://www.googleapis.com/auth/calendar.calendarlist.readonly
https://www.googleapis.com/auth/calendar.events


No broader scopes may be introduced without explicit approval.

Forbidden examples:
calendar.readonly
calendar

---

# Codex Preflight Checklist

Before implementing any user story, Codex must perform the following checks.

This checklist ensures that generated changes comply with the Zumbot CODEX Operating System.

### 1. Architecture Validation

Codex must first determine which layer is responsible for the change.

Layers:

- API layer
- Service layer
- ORM models
- SQL migrations
- Infrastructure

Rules:

- Business logic belongs in services.
- API endpoints must remain thin.
- Database schema changes must occur in SQL migrations only.
- ORM models must reflect migrations but not define schema defaults.

### 2. Database Migration Check

If a user story introduces schema changes:

Codex must:

- create a SQL migration file
- define all DB defaults in the migration
- update ORM models only as mappings

Codex must NOT:

- introduce server_default in ORM models
- modify schema without migration

Checklist:

- migration file created
- schema defaults defined in SQL
- ORM updated without server_default

### 3. API Endpoint Registration Check

When creating new endpoints:

Codex must verify:

- endpoint function exists
- router decorator is present
- router is included in application startup
- endpoint appears in API documentation

Checklist:

- endpoint implemented
- router registration verified
- application router updated

### 4. Tests Coverage Check

Every user story must include tests.

Minimum requirements:

- unit tests for business logic
- integration tests for endpoints

Checklist:

- test file added
- tests reference implemented feature
- tests pass locally

Typical locations:

tests/test_<feature>.py

### 5. Documentation Synchronization

If a feature changes behavior or adds functionality:

Codex must update documentation.

Documentation may include:

- user story file
- API documentation
- architecture documentation

Checklist:

- docs updated
- docs committed in same PR

### 6. Security Validation

For any admin or destructive operation:

Codex must verify:

- admin authentication enforced
- CSRF protection applied
- confirmation phrase required for destructive actions
- audit logging added

Checklist:

- auth required
- audit event emitted
- destructive operation protected

### Execution Rule

Codex must run this checklist mentally before generating code.

If any checklist item cannot be satisfied, Codex must adjust the implementation plan before writing code.

---

# Output Style

All responses must be:

- structured
- concise
- implementation-oriented
- aligned with Zumbot architecture

Avoid vague advice.

Prefer **clear next actions**.
