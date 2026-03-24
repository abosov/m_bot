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

## Atomic Task Isolation Contract
Atomic Task Isolation is a mandatory workflow contract for both initial story execution and follow-up execution.
It is an execution blocker, not optional guidance: Codex must refuse implementation until the prompt clearly satisfies this contract.

Every Codex task must satisfy all of the following:

1. **One task, one purpose**: each prompt must describe one independently reviewable change only.
2. **One follow-up, one finding**: each follow-up prompt must address exactly one review finding or one narrowly defined blocker only; multiple independent fixes require multiple follow-up prompts.
3. **Explicit intent**: the task must state the exact change being made, why it belongs to the current story, and what is out of scope.
4. **Explicit boundaries**: allowed files and forbidden files/areas must be declared before implementation.
5. **No scope expansion**: adjacent fixes, opportunistic cleanup, and unrelated refactors are forbidden even when discovered during implementation.
6. **Minimal patch only**: the diff must be limited to the smallest change set that satisfies the story or follow-up objective.
7. **Mandatory follow-up capture**: out-of-scope findings must be recorded as explicit follow-up work instead of being absorbed into the current run.
8. **Hard stop**: if completion requires breaking scope, touching unrelated concerns, or changing architecture outside the prompt, stop and require a new story or follow-up prompt.
9. **Epic registry alignment**: do not start a new story in an epic until the epic registry reflects the current known state of relevant prior stories, and record split/follow-up/cancelled/superseded outcomes in the registry instead of leaving them only in conversation history.

This contract is documentation-driven in this workflow. If runtime enforcement is needed, it must be introduced by a separate story rather than by broadening an active story.
Follow-up prompts are not an exception path around this contract; they must isolate one review finding or one narrowly defined blocker per run unless a new prompt explicitly redefines scope.
Review findings must be decomposed before execution. If a review produces multiple blockers or improvements, each independently reviewable item becomes its own follow-up prompt instead of being batched into one continuation run.

### Mandatory prompt contract fields
Every master or follow-up prompt must explicitly include all of the following fields so Atomic Task Isolation is auditable:
- `TASK_INTENT` or `FOLLOW-UP_INTENT` (one sentence, exact purpose).
- `OUT_OF_SCOPE` (explicit exclusions).
- `FILES_ALLOWED_TO_CHANGE` (exact boundary).
- `FILES_THAT_MUST_NOT_CHANGE` (explicit forbidden boundary).
- `ATOMIC_TASK_ISOLATION` (single purpose + hard stop condition).
- Follow-up capture rule stating that out-of-scope findings are recorded as separate follow-up work and never absorbed inline.
- Execution gate stating that Codex must refuse implementation when the prompt is missing required fields, lacks a single atomic purpose, or batches multiple follow-up findings.
- Exact declaration rule stating that Codex must restate the one-sentence task or follow-up intent before making changes.

If any required field is missing or ambiguous, execution must stop and the prompt must be corrected before implementation.
Prompt completeness is a mandatory execution gate, not a best-effort prompt-quality guideline.

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
- Include explicit forbidden file/area list when scope boundaries matter.
- Include an explicit intent statement and explicit out-of-scope statement.
- Include explicit Atomic Task Isolation language for both initial execution and follow-up execution.
- Include an explicit execution gate that tells Codex to refuse implementation when the prompt is non-atomic or underspecified.
- Require a single independently reviewable purpose, and for follow-ups require a single review finding or blocker per prompt.
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
- Prompt is missing an execution gate or treats Atomic Task Isolation as optional guidance instead of a hard contract.
- Prompt or follow-up tries to combine multiple independently reviewable fixes in one run.
- Review output contains multiple independent findings but the next follow-up prompt does not isolate exactly one of them.
- Missing constraints or allowed-file list.
- Missing explicit task intent, out-of-scope statement, or follow-up handling for out-of-scope findings.
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
- Atomic Task Isolation rules were followed, including explicit boundaries and follow-up capture for out-of-scope findings.
- Role-based design sequence was applied.
- Architecture boundaries were respected.
- Database rules were respected (including migration source-of-truth policy).
- Documentation was updated where required.
- Checks/tests from prompt were executed and reported.
- Security review passed (no secrets/credentials leakage).
- Result is minimal, clean, and ready for safe deployment.

## Automation Escalation Contract
For workflow automation stories that can re-run after review rejection, repeated reject stagnation must remain deterministic and fail-closed.

Required contract:
- Trigger escalation only from concrete workflow evidence, not heuristics.
- The minimum stagnation rule is: repeated `review_classification` gate reject plus identical reviewed diff evidence (`diff.patch` and `changed_files.txt`) across rejected runs for the same story.
- When that rule triggers, automation must materialize an explicit escalation artifact and ordinary continuation must stop until a human resolves it.
- Human resolution must be explicit and auditable with one of exactly three actions: `accept-as-is`, `force-followup`, or `abort`.
- `force-followup` may reopen ordinary automated continuation; `accept-as-is` and `abort` must not silently reopen it.
- The append-only workflow ledger may record rejection evidence, but it must not be the source of truth for whether continuation is allowed.

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
