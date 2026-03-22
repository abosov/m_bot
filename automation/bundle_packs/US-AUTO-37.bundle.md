# Story Bundle Pack
Story-ID: US-AUTO-37
Version: 1

This pack is the single source of truth for materialized story bundle files.

=== FILE: 00_story.md ===
# US-AUTO-37: Ephemeral automation paths contract

## Story ID and Title
- Story ID: `US-AUTO-37`
- Title: `Ephemeral automation paths contract`

## Objective
Define and implement a safe workflow contract for ephemeral automation-generated paths, starting with `automation/story_change_ledger.jsonl`, so this runtime side effect is not treated as normal implementation diff.

## Scope
- Classify `automation/story_change_ledger.jsonl` as an ephemeral automation artifact.
- Align happy-path behavior for `automation/scripts/run_story.sh`.
- Align happy-path behavior for `automation/scripts/finalize_story.sh`.
- Ensure scope-related validation does not treat this path as implementation drift.
- Update focused tests and workflow docs only as needed to support this contract.

## Non-goals
- Do not redesign the durable ledger architecture.
- Do not weaken US-AUTO-39 reviewed-head vs checkout-head invariants.
- Do not weaken US-AUTO-40 artifact fidelity checks.
- Do not change unrelated product, backend, frontend, database, or migration code.
- Do not introduce broad ignore rules that could hide real implementation changes.

## Dependencies
- US-AUTO-39 — reviewed_head vs checkout_head invariant.
- US-AUTO-40 — review artifact fidelity to actual HEAD diff.
- Existing automation workflow scripts for run, review, and finalize.
- Existing bundle validation and execution workflow.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Current Code Reality
- `automation/story_change_ledger.jsonl` is generated as a workflow side effect.
- Existing workflow scripts already treat this path as ephemeral for clean-tree and review-fidelity checks.
- Happy-path automation should restore this path to `HEAD` on exit so workflow evidence does not masquerade as implementation drift.
- The contract remains fragile if path handling drifts across run/review/finalize scripts.

## Target Outcome
- `automation/story_change_ledger.jsonl` is treated as an ephemeral automation path rather than normal implementation diff.
- Happy-path `run_story.sh` does not leave the repo dirty only because of this file.
- Happy-path `finalize_story.sh` does not leave the repo dirty only because of this file.
- Scope validation remains strict for real implementation changes.

=== FILE: 01_context_bundle.md ===
# US-AUTO-37: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`

## Current Code Reality
- `automation/story_change_ledger.jsonl` is a workflow-generated side effect.
- Existing scripts exclude this path from strict implementation-diff enforcement.
- Happy-path workflow should restore this path to `HEAD` on exit to keep the branch clean.

## Architectural Intent
- Introduce one explicit contract for ephemeral automation paths.
- Keep runtime-generated artifacts from masquerading as normal implementation diffs.
- Preserve strict validation for real code and workflow changes.

## Risks
- A too-broad ignore rule could hide real implementation changes.
- A too-local fix could reintroduce drift between scripts, tests, and docs.
- Incomplete lifecycle handling could fix run but still leave finalize dirty, or vice versa.

## Acceptance Notes
- Happy-path run should not leave ledger dirt in the working tree.
- Happy-path finalize should not leave ledger dirt in the working tree.
- Scope handling must remain strict for non-ephemeral file changes.

=== FILE: 02_file_scope.md ===
# US-AUTO-37: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_run_story.py`
- `tests/test_finalize_story.py`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-37.bundle.md`
- `automation/bundles/active/US-AUTO-37/**`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated CI workflows
- unrelated application code
- broad repository-wide ignore configuration unrelated to this story

=== FILE: 03_master_prompt.md ===
# US-AUTO-37 PROMPT 1 — Ephemeral automation paths contract

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-37 — Ephemeral automation paths contract.

## Goal
Implement a minimal, safe, and explicit workflow contract for `automation/story_change_ledger.jsonl` so it is treated as an ephemeral automation artifact instead of normal implementation diff, while preserving existing strict review and fidelity behavior.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_run_story.py`
- `tests/test_finalize_story.py`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-37.bundle.md`
- `automation/bundles/active/US-AUTO-37/**`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated CI workflow files
- unrelated product/runtime code
- any broad workaround that weakens real-diff validation

## Implementation Requirements
1. Treat `automation/story_change_ledger.jsonl` as an ephemeral automation path.
2. Keep the solution narrow and deterministic.
3. Ensure happy-path run does not leave this file as dirty state.
4. Ensure happy-path finalize does not leave this file as dirty state.
5. Ensure real implementation changes are still detected strictly.
6. Update focused tests and docs only as required.

## Testing
- Add or update focused tests for run behavior.
- Add or update focused tests for finalize behavior.
- Verify real implementation changes are still not masked.
- Run focused pytest targets relevant to the changed files.

## Documentation
- Update workflow docs/specs only where needed to reflect the ephemeral-path contract.
- Keep documentation aligned with actual implemented behavior.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-37: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No unrelated runner refactor was introduced
- [ ] No broad ignore rule was introduced
- [ ] No weakening of US-AUTO-39 or US-AUTO-40 invariants was introduced

## Functional Validation
- [ ] `automation/story_change_ledger.jsonl` is treated as an ephemeral automation path
- [ ] Happy-path `run_story.sh` does not leave ledger dirt
- [ ] Happy-path `finalize_story.sh` does not leave ledger dirt
- [ ] Real implementation changes remain detectable

## Verification
- [ ] Focused tests were run
- [ ] Bundle materialization and validation succeeded
- [ ] Final diff and docs were reviewed

=== FILE: 05_followups.md ===
# US-AUTO-37: Follow-Ups

## Follow-Up Prompt Queue
- Consider centralizing ephemeral-path handling if multiple paths appear in future stories.
- Follow with US-AUTO-38 for automatic rollback behavior after failed automation runs.
- Revisit stronger single-source-of-truth scope handling in a later workflow story if still needed.

## Iteration Notes
- Keep this story narrowly scoped.
- Prefer deterministic cleanup and classification over broad ignores.
- Preserve existing strict review behavior.

=== FILE: 06_manual_actions.md ===
# US-AUTO-37: Manual Actions

## Required Human Actions
- Review the updated bundle pack and confirm placeholders are fully resolved.
- Materialize the bundle.
- Validate the materialized bundle.
- Run the story after validation succeeds.
- Review `git status` after run and finalize while this story is being implemented.

## Suggested Manual Verification
- Confirm `automation/story_change_ledger.jsonl` no longer causes happy-path dirty state.
- Confirm real implementation changes are still visible to workflow checks.
- Review focused tests and final diff before PR.

## Completion Status
- [ ] Bundle placeholders resolved
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for implementation
