# Story Bundle Pack
Story-ID: US-AUTO-42
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# US-AUTO-42: Context Bundle

## Source of Truth
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`

## Current Code Reality
- The pipeline now has a stable execution chain around committed artifacts and deterministic review boundaries.
- `US-AUTO-28` exposed a narrower remaining governance bug: escalation resolution handling in `run_story.sh` is not yet fully fail-closed for invalid resolution input.
- The registry explicitly identifies `US-AUTO-42` as the next recommended atomic fix for this gap.
- This story should be implemented as a narrow follow-up, not as a continuation of the broader `US-AUTO-28` scope.

## Architectural Intent
- Treat escalation resolution as a governance gate, not a best-effort hint.
- Require valid, explicit operator-approved resolution input before continuing.
- Prefer deterministic stop behavior over silent continuation.
- Keep the boundary narrow: fix only invalid-resolution handling in `run_story.sh`, with focused tests and minimal docs updates.

## Risks
- Scope creep into broader escalation orchestration.
- Reintroducing fail-open behavior through implicit defaults.
- Updating tests incompletely so only one invalid-input class is covered.
- Documentation drifting from the actual runtime contract.

## Acceptance Notes
- The implementation remains confined to the atomic defect.
- The runtime contract becomes stricter, not looser.
- The operator receives deterministic remediation when escalation input is invalid.
- New out-of-scope findings are captured as follow-ups instead of being fixed inline.

=== FILE: 02_file_scope.md ===
# US-AUTO-42: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-42.bundle.md`
- `automation/bundles/active/US-AUTO-42/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Scope Notes
- Keep the implementation confined to the invalid escalation resolution path in `run_story.sh`.
- Prefer the smallest deterministic parser/branching change that achieves fail-closed behavior.
- Tests must target blocking behavior, not broader workflow redesign.
- If a needed fix appears to require changing escalation artifact producers or neighboring scripts, stop and create a follow-up instead.

=== FILE: 03_master_prompt.md ===
# US-AUTO-42 PROMPT 1 — Fail-Closed Escalation Resolution

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-42 — Enforce fail-closed escalation resolution.

## Goal
Implement a narrow governance hardening fix so `automation/scripts/run_story.sh` fails closed whenever escalation resolution input is malformed, missing, empty, or unknown, instead of allowing execution to continue.

## Source of Truth
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`

## Intent
Intent: enforce fail-closed escalation resolution parsing in `automation/scripts/run_story.sh` and add focused regression coverage for invalid `resolution_action` inputs.

## Out of Scope
Out of scope: escalation UX redesign; escalation schema redesign; changes to escalation producers; `AUTOMATION_RUNS_ROOT`; review/gate reuse; AI review failure handling; zone budgets; targeted test strategy work; any non-escalation governance cleanup.

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-42.bundle.md`
- `automation/bundles/active/US-AUTO-42/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Atomic Task Isolation Contract
Atomic Task Isolation is a mandatory contract for this run.

You must declare the one-sentence task intent before making changes.

You must implement exactly one narrow defect fix:
- invalid escalation resolution input in `run_story.sh` must fail closed.

You must not treat this prompt as permission to redesign escalation flow or fix adjacent governance issues.

If you discover any additional issue that is not strictly required to make invalid `resolution_action` fail closed, you must stop, leave the issue untouched, and capture it as a follow-up.

Follow-up prompts are not an exception path around Atomic Task Isolation.

## Execution Gate
Before editing files, verify that this prompt is atomic, sufficiently specified, and limited to one defect. If it is not, stop instead of proceeding.

Hard stop immediately if any required code change would:
- touch a forbidden file,
- solve more than the invalid-resolution defect,
- require producer-side escalation artifact changes,
- require redesigning operator UX or downstream review/gate behavior.

## Implementation Requirements
1. Inspect the current escalation resolution branch in `automation/scripts/run_story.sh`.
2. Remove any fail-open continuation path for invalid resolution input.
3. Treat each of the following as a deterministic failure condition:
   - missing required escalation artifact when resolution is being consumed,
   - malformed JSON,
   - missing `resolution_action`,
   - empty `resolution_action`,
   - whitespace-only `resolution_action`,
   - unknown `resolution_action`.
4. Ensure the operator-facing message identifies the invalid resolution state and tells the operator to fix the escalation artifact rather than rerun blindly.
5. Add focused regression tests in `tests/test_run_story.py` that prove execution does not continue for invalid cases.
6. Update docs only where needed to describe the fail-closed escalation resolution contract.
7. Keep the patch minimal and localized.

## Verification Requirements
- Run the focused `tests/test_run_story.py` coverage relevant to escalation resolution.
- Confirm at least one invalid-input case is blocked with deterministic stderr guidance.
- Confirm no unrelated scripts were changed.

## Follow-Up Capture Rule
If you encounter any of the following, do not fix them here; capture them as follow-ups instead:
- broader escalation policy changes,
- artifact schema redesign,
- run-dir provenance redesign,
- review/gate coupling changes,
- unrelated test-suite restructuring.

## Output
Make the required code, test, and documentation changes directly in the repository.

The result must:
- make invalid escalation resolution input fail closed;
- add focused regression coverage for malformed, missing, empty, whitespace-only, and unknown `resolution_action` values;
- keep the implementation tightly scoped to US-AUTO-42;
- avoid changes to forbidden files;
- update only the narrowest necessary documentation.

=== FILE: 04_review_checklist.md ===
# US-AUTO-42: Review Checklist

## Scope Validation
- [ ] Only the allowed files changed.
- [ ] The patch stays confined to invalid escalation resolution handling in `run_story.sh`.
- [ ] No neighboring governance work was absorbed.
- [ ] No forbidden scripts were modified.
- [ ] Any new out-of-scope issue was captured as a follow-up instead of fixed inline.

## Functional Validation
- [ ] `run_story.sh` no longer continues on malformed escalation resolution input.
- [ ] Missing required escalation artifact is fail-closed when resolution is being consumed.
- [ ] Missing `resolution_action` is fail-closed.
- [ ] Empty `resolution_action` is fail-closed.
- [ ] Whitespace-only `resolution_action` is fail-closed.
- [ ] Unknown `resolution_action` is fail-closed.
- [ ] There is no permissive default branch that silently continues execution.
- [ ] Operator messaging is deterministic and clearly instructs artifact correction.

## Verification
- [ ] Targeted regression tests were added or updated in `tests/test_run_story.py`.
- [ ] Tests prove execution is blocked for malformed JSON.
- [ ] Tests prove execution is blocked for missing `resolution_action`.
- [ ] Tests prove execution is blocked for empty or whitespace-only `resolution_action`.
- [ ] Tests prove execution is blocked for unknown `resolution_action`.
- [ ] Tests prove execution is blocked before downstream execution continues.
- [ ] `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` reflects the fail-closed escalation resolution contract if documentation changes were needed.
- [ ] `docs/90_codex/epics/US-AUTO_REGISTRY.md` remains consistent with bundle lifecycle expectations if touched.
- [ ] Existing clean-tree, preflight, and committed-HEAD boundaries remain unchanged.
- [ ] No changes were made to review, AI review, classification, or gate scripts.
- [ ] The story remains an atomic follow-up to `US-AUTO-28`, not a hidden multi-story refactor.

=== FILE: 05_followups.md ===
# US-AUTO-42: Follow-Ups

## Follow-Up Prompt Queue
- `<No follow-ups yet>`

## Iteration Notes
- Broader escalation artifact provenance or schema hardening belongs in a separate follow-up if runtime evidence shows it is needed.
- Any fix requiring `automation/scripts/escalate_story.sh` changes is out of scope for this story.
- `AUTOMATION_RUNS_ROOT` handling remains outside this story and should not be mixed into the invalid-resolution fix.
- AI review failure handling remains `US-AUTO-43`, not part of this story.
- Any future follow-up created from this story must isolate exactly one finding or blocker and must repeat the full Atomic Task Isolation gate language.

=== FILE: 06_manual_actions.md ===
# US-AUTO-42: Manual Actions

## Required Human Actions
- Materialize the bundle pack for `US-AUTO-42`.
- Validate the materialized active bundle before any run.
- Review the active bundle files in Cursor before executing the story.
- If validator fails, fix the bundle pack first instead of patching active files manually.
- After implementation, manually inspect at least one invalid escalation case to confirm `run_story.sh` fails closed with deterministic guidance.

## Execution Notes
- Bundle pack source of truth: `automation/bundle_packs/US-AUTO-42.bundle.md`
- Materialize with: `automation/scripts/materialize_story_bundle.sh US-AUTO-42`
- Validate with: `automation/scripts/validate_story_bundle.sh US-AUTO-42`
- Open active files after successful validation:
  - `automation/bundles/active/US-AUTO-42/00_story.md`
  - `automation/bundles/active/US-AUTO-42/02_file_scope.md`
  - `automation/bundles/active/US-AUTO-42/03_master_prompt.md`

## Completion Status
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for PR

## Additional Manual Verification
- Confirm the bundle contains exactly seven file sections.
- Confirm there are no nested `=== FILE: ... ===` markers inside section bodies.
- Confirm validation passes before `run_story.sh`.
- Confirm the implementation PR remains atomic and touches no forbidden files.