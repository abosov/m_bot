---
name: zumbot-user-story-workflow
description: Standard development workflow for Zumbot features, admin console tasks, architectural specifications, and atomic Codex prompts.
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

---

### Database rules

Database schema **must only change via SQL migrations**.

SQL migrations are the **single source of truth** for the database schema **and database-level defaults**.

ORM models must follow migrations and **must not define DB defaults via `server_default`**.

Python-side `default=...` is allowed only for application behavior and **must not replace migration-defined DB defaults**.

Forbidden ORM patterns (must not be generated):
- `server_default="0"`
- `server_default="false"`
- `server_default=func.now()`

Required approach:
- define DB defaults in SQL migration files;
- keep ORM models free of `server_default`.

Common mistake:
- Adding `server_default` in `database.py` after creating a migration default.

Correct approach:
- Put/adjust default in SQL migration and leave ORM without `server_default`.

Never introduce duplicate schema definitions.

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

# Output Style

All responses must be:

- structured
- concise
- implementation-oriented
- aligned with Zumbot architecture

Avoid vague advice.

Prefer **clear next actions**.