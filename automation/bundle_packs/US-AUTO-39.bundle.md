# Story Bundle Pack
Story-ID: US-AUTO-39
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-39: Re-review / Re-gate Finalized Post-Commit HEAD

## Story ID and Title
- Story ID: `US-AUTO-39`
- Title: `Re-review / Re-gate Finalized Post-Commit HEAD`

## Objective
Restore the workflow invariant that reviewed evidence, finalized branch state, and merge-ready state must all refer to the same HEAD. If finalize creates a new commit, any earlier approval must become stale until review/gate are rerun for the new finalized HEAD.

## Scope
- Define the contract for post-finalize re-review / re-gate.
- Bind review/gate evidence to an explicit HEAD identity.
- Update workflow scripts only as needed to fail closed on HEAD mismatch.
- Add or update focused tests for stale approval after finalize mutates HEAD.
- Update workflow docs and active bundle files for this story.

## Non-goals
- Do not redesign the whole run directory model.
- Do not solve all branch-wide scope issues in this story.
- Do not implement global ephemeral path policy.
- Do not implement failed-run rollback/cleanup here.
- Do not absorb US-AUTO-40, US-AUTO-41, US-AUTO-35, US-AUTO-36, US-AUTO-37, or US-AUTO-38 except for minimal plumbing strictly required for this story.

## Dependencies
- Findings and closure state from US-AUTO-32.
- Existing finalize/review/gate workflow scripts.
- Existing story bundle materialization/validation workflow.

## Source of Truth
- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-39.bundle.md`

## Current Code Reality
- US-AUTO-32 proved that pre-merge finalization can create a new commit safely.
- Existing workflow behavior can leave review/gate evidence bound to an earlier HEAD after finalize mutates branch HEAD.
- Some review flows resolve the latest run rather than a run explicitly bound to current HEAD.
- This creates a stale-approval risk where reviewed evidence may not match the finalized snapshot that is actually considered for merge.

## Target Outcome
- Finalize may still create a pre-merge finalized commit.
- That finalized HEAD becomes the only valid merge target.
- Pre-finalize approval becomes stale automatically if HEAD changes.
- Review/gate evidence must be explicitly associated with the finalized HEAD.
- Merge readiness fails closed unless reviewed HEAD == finalized HEAD == merged HEAD.

=== FILE: 01_context_bundle.md ===
# US-AUTO-39: Context Bundle

## Source of Truth

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-39.bundle.md`

## Current Code Reality

- US-AUTO-32 confirmed that pre-merge finalization can create a new commit before merge.
- Review/gate evidence may still belong to an earlier HEAD when finalize mutates the branch HEAD.
- Some review flows resolve the latest available run rather than a run explicitly bound to the current HEAD.
- This creates a stale-approval condition where reviewed evidence can differ from the finalized snapshot intended for merge.

## Architectural Intent

- Preserve durable pre-merge finalization.
- Make the finalized HEAD the canonical merge target.
- Require review/gate evidence to be explicitly bound to a specific HEAD identity.
- Fail closed when current HEAD differs from reviewed/gated HEAD.
- Restore the invariant: reviewed HEAD == finalized HEAD == merged HEAD.

## Risks

- Overreaching into broader run-resolution redesign that belongs in later stories.
- Accidentally keeping a latest-run loophole while adding partial HEAD metadata.
- Allowing operator UX to imply approval is still valid after HEAD mutation.
- Updating docs/tests incompletely and leaving the contract ambiguous.

## Acceptance Notes

- Finalize may still create a new commit before merge.
- Any approval from the pre-finalize HEAD must become stale if HEAD changes.
- Re-review / re-gate on the finalized HEAD must be required before merge readiness is restored.
- The implementation must remain narrowly scoped to this contract.

=== FILE: 02_file_scope.md ===
# US-AUTO-39: File Scope

## Files Allowed To Change

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- `tests/test_review_gate_story_run.py`
- `automation/story_change_ledger.jsonl`
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`
- `automation/bundle_packs/US-AUTO-39.bundle.md`

## Files Not Allowed To Change

- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated deployment scripts
- unrelated bundle packs
- broad workflow redesign outside HEAD-bound post-finalize approval

## Scope Notes

- Keep this story narrowly focused on post-finalize re-review / re-gate contract enforcement.
- Do not absorb US-AUTO-40 / US-AUTO-41 / US-AUTO-35 / US-AUTO-36 / US-AUTO-37 / US-AUTO-38 except for minimal shared plumbing strictly required here.

=== FILE: 03_master_prompt.md ===
# US-AUTO-39 PROMPT 1 — Re-review / Re-gate Finalized Post-Commit HEAD

## Role

You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal

Implement a fail-closed post-finalize re-review / re-gate contract so that merge readiness is valid only when review/gate evidence is explicitly bound to the current finalized HEAD.

## Source of Truth

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`

## Files Allowed To Change

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- targeted review/gate orchestration tests directly required for HEAD-bound approval
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`

## Files Not Allowed To Change

- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated deployment scripts
- unrelated workflow redesign outside this story

## Context

US-AUTO-32 proved that a pre-merge finalized commit can be created safely, but it exposed a workflow integrity bug: when finalize creates a new commit, existing review/gate evidence still belongs to the prior HEAD, so merge readiness may reflect stale approval.

The required invariant is:

- reviewed HEAD == finalized HEAD == merged HEAD

## Requirements

1. Preserve the ability of finalize to create a durable pre-merge finalized commit.
2. Make the finalized HEAD the canonical merge target.
3. Ensure pre-finalize approval becomes stale if finalize changes HEAD.
4. Require review/gate evidence to be explicitly associated with a HEAD identity.
5. Fail closed if current HEAD differs from reviewed/gated HEAD.
6. Add or update tests proving stale approval rejection and post-finalize re-approval behavior.
7. Update workflow documentation and active bundle files accordingly.

## Constraints

- Keep the implementation as small and targeted as possible.
- Do not absorb US-AUTO-40 / 41 / 35 / 36 / 37 / 38 except for minimal shared plumbing strictly required for this story.
- Do not reintroduce any fail-open behavior.
- Prefer explicit metadata and deterministic checks over latest-run heuristics.
- Preserve durable ledger behavior.

## Output

Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-39: Review Checklist

## Scope Validation

- [ ] Changes stay inside `02_file_scope.md`
- [ ] No unrelated workflow redesign was absorbed
- [ ] No fail-open path was introduced
- [ ] Changes remain focused on HEAD-bound post-finalize approval

## Functional Validation

- [ ] Finalize can still create a pre-merge finalized commit
- [ ] Pre-finalize approval becomes stale if finalize changes HEAD
- [ ] Review/gate evidence is explicitly bound to a HEAD identity
- [ ] Merge readiness fails when current HEAD differs from reviewed/gated HEAD
- [ ] Re-review / re-gate on the finalized HEAD restores readiness

## Verification

- [ ] Targeted tests cover stale approval after HEAD mutation
- [ ] Docs and active bundle files were updated consistently
- [ ] Risks and follow-ups were captured without absorbing neighboring stories

=== FILE: 05_followups.md ===
# US-AUTO-39: Follow-Ups

## Follow-Up Prompt Queue
- `<No follow-ups yet>`

## Iteration Notes
- Broader current-HEAD run resolution across all review scripts belongs in follow-up scope unless strictly required here.
- Full artifact fidelity to exact `origin/main...HEAD` diff belongs to US-AUTO-40 unless strictly required here.
- Scope single-source-of-truth cleanup belongs to US-AUTO-41 unless strictly required here.
- Ephemeral automation path policy and failed-run rollback stay out of scope for this story.

=== FILE: 06_manual_actions.md ===
# US-AUTO-39: Manual Actions

## Required Human Actions
- Materialize the bundle after pack edits.
- Validate the active bundle before execution.
- Run targeted tests for finalize/review/gate behavior.
- Simulate a flow where finalize mutates HEAD after initial approval.
- Verify stale approval is rejected and re-review/re-gate on finalized HEAD restores readiness.

## Completion Status
- [ ] Bundle materialized
- [ ] Bundle validated
- [ ] Manual verification completed
- [ ] Ready for PR