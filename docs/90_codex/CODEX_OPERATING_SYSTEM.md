# CODEX OPERATING SYSTEM

## Purpose
This document defines the mandatory operating standard for all Codex-driven changes in this repository.
It is the single source of truth for AI-assisted development workflow, architecture compliance, delivery quality, and release safety.

All future Codex prompts and resulting changes must follow this document.

## Related Codex Context Docs
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`

These documents provide persistent repository context for Codex prompts and should be read before implementing non-trivial user stories.

---

## Core Principles
1. **Documentation-first development**: changes must be reflected in relevant docs in the same prompt.
2. **Atomic delivery**: one prompt = one atomic change with clear scope.
3. **Architecture integrity**: do not break bounded contexts, service responsibilities, or integration contracts.
4. **Deterministic data ownership**: schema and migration lifecycle are explicit and controlled.
5. **Traceability**: every change includes rationale, impacted files, and checks.
6. **Deploy safety**: production-readiness checks are mandatory before release.

---

## Layer Boundaries
### Architectural boundaries
- **API / Application layer** handles transport concerns, validation, orchestration.
- **Domain layer** owns business rules, state transitions, invariants.
- **Infrastructure layer** owns external adapters (DB, Telegram, Google Calendar, queues if introduced later).
- **Configuration layer** controls environment behavior without changing code between local and production.

### Boundary rules
- Do not move business rules into transport/infrastructure code.
- Do not bypass domain rules with direct persistence shortcuts.
- Keep integrations behind explicit interfaces/adapters.
- Keep docs aligned with any architectural decision changes.

---

## Database Rules
1. **SQL migrations are the single source of truth for schema**.
2. ORM models must mirror schema but must not redefine DB defaults inconsistently.
3. **ORM models must not define database-level defaults via `server_default`**.
4. **DB defaults must be defined only in SQL migrations** (single source of truth).
5. Python-side `default=...` may be used for application behavior but must not replace migration-defined DB defaults.
6. Production schema creation/updates must run via migrations only.
7. **Production schema must never depend on `metadata.create_all`**.
8. Any schema change requires:
   - forward migration,
   - rollback strategy,
   - documentation update.

---

### Common mistake vs correct approach (DB defaults)
- Common mistake (forbidden): add `server_default="0"` / `server_default="false"` / `server_default=func.now()` in ORM models.
- Correct approach (required): define DB defaults in SQL migrations and keep ORM models free of `server_default`.

## Atomic Prompt Format
Every Codex prompt must use the following structure:

```text
US-AD-8 PROMPT 1

Goal
Context
Constraints
Files to modify
Test plan
Documentation updates
```

### Prompt rules
- Include explicit allowed file list.
- Include explicit forbidden actions (if needed).
- Keep each prompt narrowly scoped and independently verifiable.
- Do not combine unrelated refactoring with functional change.

---

## Role-based Design
Analysis and implementation must follow this role sequence without skipping roles:

1. **Architect**
   - Validate fit with current system boundaries.
   - Confirm impacted components and contracts.
2. **Data Architect**
   - Validate schema/migration impact.
   - Enforce SQL migration source-of-truth policy.
3. **UX**
   - Validate user/developer flow clarity for the proposed change.
   - Ensure communication and structure are understandable.
4. **Developer**
   - Implement only scoped changes.
   - Keep edits minimal and deterministic.
5. **Tech Writer**
   - Update docs for behavior, constraints, and operational usage.
   - Keep wording unambiguous and actionable.
6. **QA**
   - Verify requested checks.
   - Confirm only expected files changed.
7. **Security**
   - Verify no secrets, credentials, or unsafe permissions are introduced.

---

## Red Flags
Stop and revise the prompt/change if any of the following appears:
- Prompt scope includes unrelated features.
- Missing constraints or allowed-file list.
- Changes require schema evolution but no migration plan is provided.
- ORM and SQL migration defaults diverge.
- Any `server_default` is introduced in ORM models.
- Production workflow relies on `metadata.create_all`.
- Documentation is skipped for behavior or process changes.
- Security-sensitive data appears in docs, code, logs, or examples.

---

## Deployment Checks
Before deployment, verify:
1. Migration status is consistent and applied in target environment.
2. Environment variables are explicitly defined for target environment.
3. Health/readiness behavior matches environment policy.
4. Updated docs exist for changed behavior.
5. Rollback path is available (code + migrations when relevant).
6. No hidden dependency on local-only behavior.

---

## Definition of Done
A Codex task is done only when all conditions are met:
- Scope matches the atomic prompt.
- Role-based design sequence was applied.
- Architecture boundaries were respected.
- Database rules were respected (including migration source-of-truth policy).
- Documentation was updated where required.
- Checks/tests from prompt were executed and reported.
- Security review passed (no secrets/credentials leakage).
- Result is minimal, clean, and ready for safe deployment.

# LLM Output Safety Rules

To prevent corruption of bundle packs and automation artifacts, the following rules are mandatory for all LLM-generated outputs used in the Zumbot pipeline.

## Forbidden patterns

The following patterns are strictly forbidden in generated artifacts:

1. Triple backtick fences (```)
2. Nested code blocks
3. Any occurrence of triple backticks inside bundle packs or structured outputs

Reason:
Triple backticks break Markdown parsing and can corrupt bundle packs, automation artifacts, and copy/paste flows used in the Zumbot workflow.

## Required delimiter format

Structured LLM outputs must use sentinel markers instead of Markdown fences.

Example format:

=== FILE: 00_story.md ===
content

=== FILE: 01_context_bundle.md ===
content

## Rationale

This rule guarantees that:
- bundle packs remain parseable
- Markdown rendering does not break
- Cursor and Codex pipelines remain stable