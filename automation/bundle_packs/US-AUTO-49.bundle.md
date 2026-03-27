# Story Bundle Pack
Story-ID: US-AUTO-49
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-49 — Scope validation ignores committed active-story bundle artifacts

## Story ID and Title
- **Story ID:** US-AUTO-49
- **Title:** Scope validation ignores committed active-story bundle artifacts

## Objective
Make story-run scope validation fail closed on true out-of-scope implementation changes while ignoring already-committed bundle artifacts for the active story that were intentionally materialized and committed before `run_story.sh` started.

This story exists to restore a valid execution path for atomic follow-ups such as `US-AUTO-28-F1` without weakening scope enforcement for Codex-produced changes.

## Scope
In scope:
- adjust the story-run scope-baseline logic so committed active-story bundle artifacts for the same story are excluded from implementation-delta scope validation
- preserve fail-closed behavior for all actual Codex-produced tracked and untracked changes outside the allowed file list
- add regression coverage for the committed-bundle-artifact scenario and for a true out-of-scope implementation change in the same execution path
- keep the change isolated to runtime orchestration and its tests

Out of scope:
- changing story bundle format or validator contract
- changing review-stage classification rules
- changing epic registry format
- changing bundle commit handoff policy from `US-AUTO-41`
- changing `US-AUTO-28-F1` implementation logic itself
- broad retry, escalation, UX, or review-pipeline redesign

## Non-goals
- do not relax allowed-file enforcement globally
- do not ignore uncommitted bundle artifacts
- do not ignore bundle artifacts for other stories
- do not introduce a fallback mode when story identity or artifact provenance cannot be determined
- do not modify review gate, finalize flow, or registry automation

## Dependencies
- `US-AUTO-41` story artifact commit handoff before run must remain the canonical prerequisite
- active bundle structure and validator contract defined by `STORY_BUNDLE_SPEC.md` and `validate_story_bundle.sh`
- existing allowed-files enforcement in the story-run pipeline must remain fail closed
- `US-AUTO-28-F1` stays blocked until this orchestration defect is fixed

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- current test coverage for story-run orchestration and scope validation

## Current Code Reality
Current workflow correctly requires bundle materialization and commit before a story run, but runtime scope validation still treats those already-committed active-story bundle artifacts as if they were part of the current implementation delta.

That causes a false reject before review stage even when Codex only changed allowed implementation files. The defect is orchestration-level: scope validation is using an insufficient baseline for runtime changes and does not distinguish committed story artifacts from Codex-produced implementation edits.

## Target Outcome
After this story:
- committed active-story bundle artifacts for the same story are ignored by scope validation during the run
- real implementation changes are still validated strictly against the allowed file list
- if story identity, artifact provenance, or baseline derivation is ambiguous, the pipeline fails closed
- `US-AUTO-28-F1` can be rerun only after this story is merged and the branch state is clean

## Atomic Task Isolation Contract
- This story fixes exactly one problem: false out-of-scope detection caused by committed active-story bundle artifacts being counted in runtime scope validation.
- Allowed implementation surface is limited to runtime orchestration and its tests.
- No changes to review logic, registry schema, bundle validator schema, or follow-up story content.
- If the implementation requires touching another pipeline stage or weakening scope enforcement semantics, stop and record a follow-up instead of expanding this story.
- The patch must preserve fail-closed behavior and determinism.

## Risks
### Complexity
- **Complexity:** Medium

### Risk
- **Risk:** Medium

### Blast Radius
- **Blast Radius:** Medium

### Main Risks
- a too-broad ignore rule could accidentally hide true out-of-scope changes
- story identity matching could be implemented loosely and misclassify artifacts from another story
- regression risk in runtime diff/baseline handling if the ignore rule is applied after rather than before authoritative change classification

### Risk Controls
- ignore only committed artifacts for the active story ID
- keep all other files subject to normal allowed-files checks
- add regression tests for both the valid ignore path and the reject path
- fail closed if the active story ID cannot be derived or the artifact path does not match the canonical story locations

## Manual Actions
- materialize this bundle to `automation/bundles/active/US-AUTO-49/`
- validate the bundle before any branch work
- update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so `US-AUTO-49` becomes the current blocker-follow-up and `US-AUTO-28-F1` remains blocked pending this fix
- create a dedicated branch for this story
- commit bundle artifacts before running `automation/scripts/run_story.sh US-AUTO-49`
- after merge, rerun selection logic from the registry; the expected next candidate is `US-AUTO-28-F1`

## Acceptance Notes
- bundle must pass `materialize_story_bundle.sh US-AUTO-49` and `validate_story_bundle.sh US-AUTO-49`
- story run must ignore already-committed bundle artifacts for `US-AUTO-49` when evaluating implementation scope
- story run must still reject a true out-of-scope implementation file change
- no validator-contract files or review-stage logic may be changed
- deterministic review outcome must remain possible because the runtime diff presented for review contains only the actual implementation delta

=== FILE: 01_context_bundle.md ===
# Context Bundle — US-AUTO-49

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- runtime orchestration scripts and their tests

## Current Code Reality
Recent execution of `US-AUTO-28-F1` reproduced a workflow blocker before review stage:
- Codex produced useful in-scope implementation edits
- scope validation also counted already-committed bundle artifacts for the active story
- the run failed even though the story logic itself was not the problem

The defect is not inside `US-AUTO-28-F1`. It is an orchestration contract gap between:
- committed story artifacts required before run, and
- runtime scope validation that should assess only the Codex-produced implementation delta

## Architectural Intent
The pipeline should preserve both of these invariants simultaneously:
1. active-story bundle artifacts must be committed before run
2. runtime scope validation must evaluate only the implementation delta created by the run

Therefore the correct fix is a narrow baseline/provenance refinement in runtime orchestration, not a relaxation of scope enforcement and not a change to bundle policy.

## Risks
- accidental scope weakening if bundle artifact ignores are not tied to the active story ID
- accidental cross-story leakage if canonical artifact paths are not enforced
- regression in change accounting if ignored files are excluded too late in the process
- temptation to “fix” this in review or registry logic instead of runtime orchestration

## Acceptance Notes
The implementation is acceptable only if:
- it ignores committed bundle artifacts for the same active story
- it keeps rejecting all true out-of-scope implementation changes
- it fails closed on ambiguous provenance
- it leaves `US-AUTO-28-F1` untouched and merely unblocks its future rerun path

=== FILE: 02_file_scope.md ===
# File Scope — US-AUTO-49

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/story_change_ledger.jsonl`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- `automation/bundle_packs/US-AUTO-49.bundle.md`
- `automation/bundles/active/US-AUTO-49/**`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Scope Notes
- This is a narrow orchestration-only story.
- Allowed change types:
  - derive or refine runtime scope baseline for the active story
  - exclude canonical committed bundle artifacts for the same story from implementation-delta scope validation
  - add regression tests covering the ignore path and reject path
- Hard scope boundaries:
  - do not modify bundle format, registry logic, review logic, or gate logic
  - do not relax scope enforcement for any non-bundle implementation file
  - do not ignore artifacts for a different story ID
  - do not introduce heuristics that silently continue on ambiguous path matching
- Fail closed rule:
  - if the script cannot determine that a changed file is a canonical committed bundle artifact for the active story, it must be treated as a normal changed file and validated normally

=== FILE: 03_master_prompt.md ===
# Master Prompt — US-AUTO-49

## Role
You are implementing a narrow runtime-orchestration fix in the US-AUTO pipeline.

## Goal
Refine story-run scope validation so that already-committed canonical bundle artifacts for the active story are ignored during implementation-delta scope validation, while all true implementation changes remain strictly enforced.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/story_change_ledger.jsonl`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- `automation/bundle_packs/US-AUTO-49.bundle.md`
- `automation/bundles/active/US-AUTO-49/**`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Atomic Task Isolation Contract
- Restate the task intent in one sentence before making changes.
- Fix exactly one issue: committed active-story bundle artifacts are incorrectly counted as scope-relevant implementation changes during the run.
- Do not change any other pipeline stage.
- Do not weaken fail-closed behavior.
- Do not broaden the ignore rule beyond canonical bundle artifacts for the active story.
- If the minimal fix appears to require touching additional files or stages, stop and surface that as a follow-up instead of expanding scope.

## Execution Gate
- Hard stop unless the implementation can be completed only within the allowed files.
- Hard stop if you cannot prove that the ignored paths are canonical bundle paths for the active story.
- Hard stop if the proposed logic would ignore uncommitted artifacts, artifacts for another story, or non-bundle implementation files.
- Hard stop if tests cannot cover both:
  - the valid same-story committed-bundle ignore path
  - the reject path for a real out-of-scope implementation change
- No fallback mode, no best-effort scope relaxation, no silent continue.

## Implementation Requirements
- Refine runtime change accounting in `automation/run_codex_task.sh` so committed canonical bundle artifacts for the active story are excluded before allowed-files scope validation is evaluated for the implementation delta.
- Preserve existing fail-closed semantics for every other changed file.
- Canonical bundle artifact paths are limited to:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
  - `automation/bundles/active/<STORY_ID>/...`
- The ignore rule must apply only when `<STORY_ID>` matches the active story being run.
- If story ID derivation or path matching is ambiguous, treat the file as normal and enforce existing scope validation.
- Add regression tests in `tests/test_run_codex_task.py` that prove:
  - same-story committed bundle artifacts do not trigger a scope failure
  - a true out-of-scope implementation file still triggers a scope failure
- Keep the patch deterministic and minimal.

## Verification Requirements
- Run targeted tests for `tests/test_run_codex_task.py`
- Verify no forbidden file changed
- Verify the implementation delta presented to downstream review excludes only the canonical same-story bundle artifacts and nothing else
- Verify the reject path still fails closed for a true out-of-scope implementation file

## Output
Provide:
- a minimal patch in the allowed files only
- targeted test evidence
- a brief note confirming that scope validation still fails closed for all non-canonical or cross-story changes

=== FILE: 04_review_checklist.md ===
# Review Checklist — US-AUTO-49

## Scope Validation
- Confirm only these files changed:
  - `automation/run_codex_task.sh`
  - `tests/test_run_codex_task.py`
- Reject if any forbidden file changed.
- Reject if the implementation ignores uncommitted artifacts.
- Reject if the implementation ignores artifacts for a different story ID.
- Reject if the implementation ignores non-canonical paths or uses loose substring matching.
- Reject if the implementation moves this logic into review, gate, finalize, or registry code.

## Functional Validation
- Confirm the runtime orchestration excludes only canonical committed bundle artifacts for the active story:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
  - `automation/bundles/active/<STORY_ID>/...`
- Confirm the active story ID is used as the matching boundary.
- Confirm ambiguous or unmatched paths are still validated normally.
- Confirm a true out-of-scope implementation file still fails the run.
- Confirm the change preserves fail-closed semantics.

## Verification
### Required Evidence
- targeted test execution for `tests/test_run_codex_task.py`
- evidence that same-story committed bundle artifacts do not cause a false scope reject
- evidence that a real out-of-scope implementation file still causes a reject

### HARD BLOCK — REJECT IF ANY APPLY
- any scope expansion beyond runtime orchestration and its tests
- any weakening of allowed-files enforcement
- any ignore rule broader than canonical same-story bundle artifacts
- any fallback path that continues when story identity or provenance is ambiguous
- missing regression coverage for the reject path
- review outcome cannot be expressed as binary `APPROVE` or `REJECT`

### Binary Decision
- **APPROVE** only if all scope, functional, and verification checks pass
- **REJECT** otherwise

=== FILE: 05_followups.md ===
# Follow-Ups — US-AUTO-49

## Follow-Up Prompt Queue
1. **US-AUTO-28-F1 rerun after unblock**
   - Preconditions:
     - `US-AUTO-49` merged to `main`
     - working tree clean
     - latest run directory for `US-AUTO-49` analyzed and resolved
   - Intent:
     - rerun `US-AUTO-28-F1` now that false scope rejection from committed bundle artifacts is removed

2. **Optional future hardening if needed**
   - Only if evidence shows additional provenance edge cases not covered by this fix
   - Must remain a separate atomic story and not be folded into `US-AUTO-49`

## Iteration Notes
- `US-AUTO-49` is intentionally atomic and should not absorb `US-AUTO-28-F1` logic.
- Registry logic for this iteration:
  - `US-AUTO-49` becomes the active blocker-follow-up
  - `US-AUTO-28-F1` remains blocked by the scope-baseline contract until `US-AUTO-49` is merged
- This story exists to restore pipeline consistency, not to redesign the full orchestration model.

=== FILE: 06_manual_actions.md ===
# Manual Actions — US-AUTO-49

## Required Human Actions
1. Save this bundle pack to:
   - `automation/bundle_packs/US-AUTO-49.bundle.md`

2. Materialize the bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-49`

3. Validate the bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-49`

4. Update epic registry logic in:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`
   - Set `US-AUTO-49` as the current blocker-follow-up with status `Bundle Ready`
   - Keep `US-AUTO-28-F1` blocked pending this orchestration fix
   - Keep notes that `US-AUTO-28-F1` should not be rerun before `US-AUTO-49` merges

5. Create a dedicated branch from updated `main`

6. Commit the materialized bundle artifacts for `US-AUTO-49`

7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-49`

8. Analyze the resulting latest run directory:
   - `automation/scripts/analyze_story_run.sh US-AUTO-49`

9. Continue normal review pipeline only if the run succeeds through scope validation and produces a reviewable implementation delta

10. After merge:
   - return to `main`
   - pull latest `main`
   - remove working branches
   - re-evaluate the registry and resume with `US-AUTO-28-F1`

## Completion Status
- Bundle drafted: complete
- Materialize required: pending
- Validate required: pending
- Registry sync required: pending
- Branch creation required: pending
- Bundle artifact commit required: pending
- Story run required: pending
- Run analysis required: pending
- Merge and rerun selection: pending