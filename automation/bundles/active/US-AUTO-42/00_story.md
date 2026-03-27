# US-AUTO-42 — Enforce fail-closed escalation resolution

## Story ID and Title
- **Story ID:** `US-AUTO-42`
- **Title:** `Enforce fail-closed escalation resolution`

## Objective
Close the fail-open path in `automation/scripts/run_story.sh` so malformed, missing, or unknown escalation `resolution_action` values cannot allow execution to continue. The script must fail closed with deterministic operator guidance whenever escalation resolution input is not valid.

## Scope
- Harden escalation resolution handling in `automation/scripts/run_story.sh`.
- Require deterministic fail-closed behavior for:
  - missing escalation artifact when resolution is required,
  - malformed escalation JSON,
  - missing `resolution_action`,
  - unknown `resolution_action`,
  - empty or whitespace-only `resolution_action`.
- Add focused regression tests that prove invalid escalation resolution input cannot continue execution.
- Update workflow documentation only where needed to make the fail-closed escalation contract explicit.
- Materialize and validate the bundle for `US-AUTO-42`.

## Non-goals
- Do not redesign escalation UX.
- Do not change escalation policy beyond invalid-resolution fail-closed enforcement.
- Do not redesign `review_gate_story_run.sh` or escalation artifact producers.
- Do not broaden scope into `AUTOMATION_RUNS_ROOT`, review reuse, AI review failure handling, or pipeline zoning.
- Do not add auto-repair, auto-defaulting, or permissive fallback branches.
- Do not modify runtime runner behavior in `automation/run_codex_task.sh`.
- Do not implement new story-registry ordering logic beyond the documentation updates strictly required for this story.

## Dependencies
- `US-AUTO-41` — canonical `materialize -> commit_story_artifacts -> run_story` handoff.
- `US-AUTO-44` — deterministic preflight and operator remediation contract.
- `US-AUTO-46` — committed-HEAD fail-closed review boundary.
- `US-AUTO-28` — escalation-gate work that exposed the fail-open defect this story isolates.

## Source of Truth
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md` (defect origin/context only)

## Current Code Reality
- The automation workflow already enforces fail-closed behavior at several boundaries: clean-tree, preflight, validation, deterministic review reuse, and committed-HEAD review boundary.
- `US-AUTO-28` review surfaced a remaining governance defect: invalid escalation resolution input in `run_story.sh` can still allow continuation instead of forcing an explicit stop.
- That defect is narrower than the broader anti-cycle stories and is suitable for an isolated follow-up fix.
- The current next-step planning already identifies `US-AUTO-42` as the atomic follow-up for this gap.

## Target Outcome
- `run_story.sh` must treat invalid escalation resolution input as a hard stop.
- No malformed or unknown `resolution_action` may fall through to execution.
- Operator output must explain exactly why execution stopped and what artifact must be fixed.
- Targeted tests must cover the invalid-input cases and prove continuation does not occur.
- Documentation must describe the fail-closed escalation contract without broadening scope into adjacent stories.

## Atomic Task Isolation Contract
### Single Purpose
This story exists for one purpose only: eliminate fail-open continuation when `run_story.sh` processes invalid escalation resolution input.

### Exact Intent Statement
Implement a narrow fail-closed fix in `automation/scripts/run_story.sh` so invalid escalation `resolution_action` values always stop execution with deterministic guidance.

### Explicit Out-of-Scope
- escalation UX redesign
- escalation artifact schema redesign
- escalation retry behavior
- AI review failure handling
- `AUTOMATION_RUNS_ROOT` handling
- review/gate recomputation logic
- pipeline zone budgets
- test strategy optimization
- any non-escalation governance refactor

### Allowed File Boundary
Only the files listed in `02_file_scope.md` may change.

### Forbidden File Boundary
All files and directories listed in `02_file_scope.md` as forbidden are out of bounds, even if they appear related.

### Hard-Stop Condition
If the fix requires changes outside the allowed file boundary or requires solving more than the single invalid-resolution defect, stop and record a follow-up instead of continuing.

### Follow-Up Rule
Any newly discovered issue outside the single invalid-resolution defect must be captured in `05_followups.md` and, if needed, the epic registry — never absorbed inline into this story.

### Review-Finding Isolation Rule
Any follow-up prompt created from this story must isolate exactly one review finding or one narrowly defined blocker. Follow-up prompts are not an exception path around Atomic Task Isolation.

## Allowed Files
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-42.bundle.md`
- `automation/bundles/active/US-AUTO-42/**`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`
- any other `automation/scripts/*` files not explicitly allowed above

## Risks
- Overfitting the fix to one happy-path artifact shape instead of all invalid-input cases.
- Accidentally introducing a permissive default branch that recreates fail-open behavior.
- Expanding into adjacent governance fixes and losing atomicity.
- Weak tests that only assert messaging instead of proving execution is blocked.

## Manual Actions
- Review the materialized bundle before execution.
- Validate the bundle before running the story.
- Review `run_story.sh` output manually for deterministic fail-closed messaging on at least one invalid escalation case.

## Acceptance Notes
- Invalid escalation resolution input must never continue execution.
- There must be no permissive default branch for unknown `resolution_action`.
- Tests must prove fail-closed behavior for malformed, missing, and unknown resolution values.
- The story must remain atomic and must not absorb neighboring governance work.

