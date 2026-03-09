# PROJECT CONTEXT UPDATE PROTOCOL

## 1) Purpose
This protocol defines when and how persistent Codex context docs must be updated so implementation prompts stay accurate and architecture-safe.

## 2) Files Covered
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`

## 3) Mandatory Update Triggers
Update context docs in the same story/PR when changes affect:
- Architecture boundaries.
- Repository structure or module ownership.
- Source-of-truth rules (schema/process ownership).
- API routing zones (public/private/admin split or router locations).
- Security boundaries.
- Destructive operation rules.
- Regression-critical runtime flows.

## 4) Optional Update Triggers
Update may be skipped for:
- Purely local code changes with no context impact.
- Test-only changes with no architectural/process implications.
- Copy-only/text polish that does not alter meaning or boundaries.

## 5) Update Ownership by Role
- Architect: validates boundaries and structural impact.
- Data Architect: validates schema ownership and migration policy.
- UX: validates flow clarity and user-surface implications.
- Technical Writer: edits docs for operational clarity and consistency.
- QA: verifies docs align with implemented behavior/paths.
- Security: validates safety boundaries and unsafe-instruction absence.

## 6) PR Rule
Any architecture-affecting implementation must include required context doc updates in the same PR.

## 7) Anti-Staleness Rule
Implementation must not contradict persistent context docs. If contradiction is found, docs must be updated before merge.

## 8) Prompt Reference Rule
Before implementation read:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`

## 9) Review Checklist
- Docs match current repository structure.
- Source-of-truth statements are correct.
- Module paths are not outdated.
- No unsafe or security-weakening instructions are present.
