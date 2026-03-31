# Story Bundle Pack
Story-ID: US-AUTO-54
Version: 1

=== FILE: 00_story.md ===
## Story ID and Title
US-AUTO-54 — Committed-HEAD review diff fidelity for US-AUTO-28-F1 rerun artifacts

## Objective
Restore deterministic `review_gate_story_run.sh` fidelity for the exact committed-head rerun path reproduced by `US-AUTO-28-F1`, so `review_diff_patch_mismatch` is emitted only when the pinned rerun evidence is truly stale or inconsistent.

The story is intentionally narrow: diagnose and fix the review-boundary comparison for the exact rerun-artifact path that still rejects after a clean committed-head rerun with matching manifest HEAD.

## Scope
In scope:
- inspect and correct the committed-head rerun diff comparison logic at the review gate boundary
- keep the change limited to the exact rerun-artifact fidelity path used by `review_gate_story_run.sh`
- add focused regression coverage for the reproduced `US-AUTO-28-F1` rerun case and for at least one true mismatch case that must still reject
- preserve fail-closed behavior and current external reject semantics outside the exact defect being fixed

Out of scope:
- new orchestration stages
- retry logic, rerun automation, continuation policy, escalation policy, or operator UX redesign
- broad refactors across unrelated pipeline scripts
- changing review classification policy or relaxing review boundary guards
- reopening `US-AUTO-28-F1` implementation scope

## Non-goals
- do not change `run_story.sh`
- do not widen `run_codex_task.sh` scope unless strictly required to preserve committed-head rerun diff fidelity and supported by failing evidence
- do not alter manual-finish continuation semantics from `US-AUTO-52`
- do not change bundle validator behavior
- do not convert governance rejects into approvals

## Dependencies
- US-AUTO-46 — review operates strictly on committed HEAD
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-50 — structured AI review contract and stable diff/story-artifact filtering baseline
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-53 — committed-HEAD `diff.patch` review fidelity baseline
- US-AUTO-28-F1 — reproduced committed-head rerun path that exposed the remaining blocker

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- pinned committed-head rerun evidence model already established by the `US-AUTO-28-F1` observation recorded in the registry
- existing review-boundary invariants already merged on `main`

## Current Code Reality
The registry records that `US-AUTO-28-F1` implementation is complete and that the remaining blocker is a downstream committed-head review artifact fidelity issue on rerun artifacts, specifically a `review_diff_patch_mismatch` rejection after a clean committed-head rerun with matching manifest HEAD.

`US-AUTO-53` already hardened committed-head `diff.patch` generation so downstream review compares the committed implementation diff represented by the pinned run. Despite that, the exact `US-AUTO-28-F1` rerun path can still reject in `review_gate_story_run.sh`, which means a narrower rerun-artifact comparison defect remains at the review boundary.

The current story must therefore stay tightly constrained to the review gate’s handling of pinned rerun artifacts and must not reopen unrelated runtime or orchestration behavior.

## Target Outcome
After implementation:
- a clean committed-head rerun with matching manifest HEAD and matching committed implementation diff for the exact `US-AUTO-28-F1` style rerun path no longer rejects with `review_diff_patch_mismatch`
- true mismatch cases still reject deterministically with the existing fail-closed behavior
- external contracts remain stable unless the existing defect makes a contract-preserving correction necessary
- regression coverage proves both acceptance of the exact good rerun path and rejection of real mismatch paths

## Atomic Task Isolation Contract
This story is atomic and must remain atomic.

Hard boundaries:
- solve exactly one problem: review-gate diff fidelity for the exact committed-head rerun artifact path
- restrict implementation to the minimum code and tests needed to correct that defect
- do not combine validation redesign, retry policy, escalation logic, UX improvements, or bundle governance changes into this story
- if a broader issue is discovered, stop at the narrowest safe fix and record the remainder in follow-ups instead of widening the story

Fail-closed requirement:
- when evidence is incomplete, stale, malformed, or ambiguous, the pipeline must still reject rather than silently accept
- the fix must reduce false mismatch on the reproduced rerun path without introducing fail-open behavior

## Risks
- **Complexity:** Medium
- **Risk:** Medium
- **Blast Radius:** Narrow

Primary risks:
- scope drift into broader review or orchestration logic
- accidentally weakening true mismatch rejection behavior
- coupling the fix to `US-AUTO-28-F1` in a way that is too bespoke instead of correcting the exact review-boundary invariant
- regression in review gate evidence handling for already-stable stories

Mitigations:
- keep file scope narrow
- preserve existing reject semantics for malformed or stale evidence
- add focused tests for exact accept and reject boundaries
- avoid touching unrelated scripts unless failing evidence proves they are the true defect source

## Manual Actions
- update the registry entry for `US-AUTO-54` from `Planned` to `Bundle Drafted` when this bundle is materialized and validated
- keep `US-AUTO-28-F1` as `Implemented`
- keep `US-AUTO-54` as the next recommended story until the implementation lands and is merged
- if the investigation reveals a broader issue than review-gate rerun fidelity, split that broader issue into a new follow-up instead of widening this story

## Acceptance Notes
This story is complete only if all of the following are true:
- the bundle materializes and validates cleanly
- the implementation remains within the declared file scope
- a focused regression test reproduces the clean committed-head rerun acceptance case
- a focused regression test proves a real mismatch still rejects
- the final behavior remains fail-closed for malformed, stale, or inconsistent rerun evidence
- no unrelated runtime or orchestration behavior is changed as part of this story

=== FILE: 01_context_bundle.md ===
## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- existing committed-head review boundary rules merged through `US-AUTO-46`, `US-AUTO-50`, `US-AUTO-52`, and `US-AUTO-53`

## Current Code Reality
The epic registry identifies `US-AUTO-54` as the next recommended story and describes a narrow remaining blocker: after `US-AUTO-28-F1` completed on committed HEAD, `run_story.sh` and `analyze_story_run.sh` succeeded on clean committed state with matching HEAD consistency, but `review_gate_story_run.sh` still rejected with `review_diff_patch_mismatch`.

This means:
- the remaining defect is downstream of the already-fixed implementation work in `US-AUTO-28-F1`
- the problem is not a dirty tree, stale HEAD, or incomplete implementation in that story
- the defect lives at the committed-head review boundary for rerun artifacts, not in general story execution

The current story should therefore target the narrowest boundary that can explain a false `review_diff_patch_mismatch` on rerun artifacts after a clean committed-head rerun.

## Architectural Intent
The automation pipeline is intentionally fail-closed.

For this story, architectural intent is:
- preserve committed-head fidelity at the review boundary
- compare the exact implementation diff represented by the pinned rerun evidence
- reject when evidence is truly stale, malformed, or inconsistent
- avoid broadening the fix into orchestration or continuation semantics
- keep deterministic outcomes so the same committed rerun evidence produces the same review gate decision

## Risks
- a too-broad fix could destabilize already-merged review boundary behavior
- a too-narrow workaround could overfit the `US-AUTO-28-F1` case and miss the actual invariant
- relaxing mismatch handling could introduce false approvals
- editing multiple scripts without proof would increase regression risk and reduce atomicity

## Acceptance Notes
Preferred implementation shape:
- fix the mismatch at `review_gate_story_run.sh` if that is where the false comparison occurs
- only touch additional files if failing evidence shows the gate is faithfully consuming incorrect upstream artifacts
- add regression tests that cover the reproduced good rerun path and a true mismatch reject path
- keep the story fail-closed and narrow

=== FILE: 02_file_scope.md ===
## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-54.bundle.md`
- `automation/bundles/active/US-AUTO-54/00_story.md`
- `automation/bundles/active/US-AUTO-54/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-54/02_file_scope.md`
- `automation/bundles/active/US-AUTO-54/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-54/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-54/05_followups.md`
- `automation/bundles/active/US-AUTO-54/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_run_codex_task.py`
- any file outside the explicit allowlist above

## Scope Notes
Allowed change types:
- minimal logic correction in `review_gate_story_run.sh` for the exact committed-head rerun diff fidelity defect
- focused regression additions or updates in `tests/test_review_gate_story_run.py`
- registry status update for `US-AUTO-54`
- story artifact materialization for this story

Disallowed change types:
- orchestration redesign
- retry loops, continuation logic changes, or operator UX enhancements
- broad refactors across review pipeline scripts
- changing tests to redefine stable external contracts
- widening the story to include unrelated review or runtime defects

If the defect cannot be fixed within this allowlist without violating atomicity, stop and record a follow-up instead of expanding scope.

=== FILE: 03_master_prompt.md ===
## Role
You are the implementation agent for the US-AUTO Codex automation pipeline. Work as a strict fail-closed engineer operating inside a narrow review-boundary follow-up.

## Goal
Implement `US-AUTO-54` as a tightly scoped correction to committed-head review diff fidelity for the exact `US-AUTO-28-F1` rerun artifact path, so `review_gate_story_run.sh` stops emitting false `review_diff_patch_mismatch` rejects for that clean rerun case while preserving true mismatch rejection.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- the active `US-AUTO-54` bundle files after materialization

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-54.bundle.md`
- `automation/bundles/active/US-AUTO-54/00_story.md`
- `automation/bundles/active/US-AUTO-54/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-54/02_file_scope.md`
- `automation/bundles/active/US-AUTO-54/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-54/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-54/05_followups.md`
- `automation/bundles/active/US-AUTO-54/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_run_codex_task.py`
- any file outside the explicit allowlist above

## Atomic Task Isolation Contract
This is a narrow follow-up.

Hard rules:
- fix exactly one defect: false `review_diff_patch_mismatch` for the exact committed-head rerun artifact path
- preserve fail-closed behavior
- do not redesign the pipeline
- do not reopen `US-AUTO-28-F1`
- do not change tests to weaken stable external behavior contracts
- do not expand into unrelated scripts unless failing evidence proves the gate script is not the true defect boundary and the change is still necessary to preserve this story’s narrow objective

If you discover a separate defect:
- do not fix it in this story
- record it as a follow-up note instead

## Execution Gate
Before editing:
1. confirm the working tree is clean except for approved story artifacts
2. materialize and validate the bundle
3. update the registry entry for `US-AUTO-54` to reflect active drafting/execution state
4. commit story artifacts before `run_story.sh`
5. run only within a feature branch, never on `main`

During implementation:
- prefer the smallest code change that restores exact rerun fidelity
- keep evidence deterministic
- maintain fail-closed reject behavior for malformed, stale, or inconsistent evidence

## Implementation Requirements
- inspect the exact comparison that produces `review_diff_patch_mismatch` in `review_gate_story_run.sh`
- identify why the clean committed-head rerun path can still be treated as mismatched after `US-AUTO-53`
- correct the comparison at the narrowest safe boundary
- add or update focused tests in `tests/test_review_gate_story_run.py` for:
  - acceptance of the exact clean committed-head rerun path
  - rejection of a true mismatch path
- preserve external reject codes and fail-closed semantics unless the false mismatch bug itself requires a contract-preserving correction

## Verification Requirements
Run only the minimum relevant verification:
- `automation/scripts/materialize_story_bundle.sh US-AUTO-54`
- `automation/scripts/validate_story_bundle.sh US-AUTO-54`
- focused pytest for `tests/test_review_gate_story_run.py`
- any additional narrow verification only if directly required by the changed code
- after commit, run:
  - `automation/scripts/run_story.sh US-AUTO-54`
  - `automation/scripts/analyze_story_run.sh US-AUTO-54`

Do not claim success unless:
- tests pass
- scope remains narrow
- analysis confirms the current run corresponds to current HEAD
- no unrelated files were changed

## Output
Produce:
- the minimal implementation diff within allowed files
- focused regression coverage
- registry update for `US-AUTO-54`
- concise execution notes in commit/PR text describing that this story fixes rerun review diff fidelity at the gate boundary and preserves fail-closed behavior

If the defect cannot be fixed without widening scope, stop and record the blocker instead of forcing a broader change.

=== FILE: 04_review_checklist.md ===
## Scope Validation
APPROVE only if all are true:
- changed files are limited to the allowlist in `02_file_scope.md`
- implementation remains focused on `review_gate_story_run.sh` and `tests/test_review_gate_story_run.py`
- no unrelated runtime, orchestration, continuation, or UX logic was modified
- `US-AUTO-28-F1` is not reopened or widened
- registry/story artifact updates are limited to this story

REJECT if any are true:
- any file outside the allowlist changed
- the change touches `run_story.sh`, `run_codex_task.sh`, `analyze_story_run.sh`, or other disallowed scripts without explicit bundle authorization
- the story attempts to solve multiple pipeline problems at once
- tests are altered to weaken stable external behavior contracts instead of fixing logic

## Functional Validation
APPROVE only if all are true:
- the exact clean committed-head rerun case equivalent to the recorded `US-AUTO-28-F1` path no longer fails with false `review_diff_patch_mismatch`
- a true mismatch case still rejects deterministically
- fail-closed behavior remains intact for malformed, stale, or inconsistent evidence
- no new fail-open path is introduced

REJECT if any are true:
- the story only masks the mismatch without correcting the comparison invariant
- a real mismatch can now pass
- malformed or stale evidence is accepted
- behavior changes rely on broad special-casing rather than a narrow invariant-preserving fix

## Verification
Required evidence:
- bundle materialize succeeds
- bundle validate succeeds
- focused `pytest` for `tests/test_review_gate_story_run.py` passes
- post-commit `run_story.sh US-AUTO-54` completes for the story
- `analyze_story_run.sh US-AUTO-54` shows evidence aligned with current HEAD

HARD BLOCK:
- missing materialize or validate success
- missing focused regression coverage
- missing proof of a true mismatch reject case
- dirty-tree or stale-run evidence at review time
- any mismatch between declared scope and actual changed files

Final decision must be binary:
- `APPROVE`
- `REJECT`

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue
- If `US-AUTO-54` proves that the remaining defect is upstream of `review_gate_story_run.sh` and cannot be corrected without widening scope, create a new narrow follow-up for the exact upstream artifact-construction defect instead of expanding this story.
- If broader operator guidance is needed after the fidelity fix, keep that as a separate operator UX story and do not fold it into `US-AUTO-54`.
- If a second class of rerun artifact mismatch is discovered that is not the same invariant as the `US-AUTO-28-F1` path, split it into a separate follow-up.

## Iteration Notes
- Selected story: `US-AUTO-54`
- Reason selected: it is marked as the next recommended story in the registry, is P1, has no unresolved predecessor that blocks it, and targets the exact remaining blocker after `US-AUTO-28-F1` was closed as implemented.
- Atomicity review: acceptable as a single narrow follow-up because it targets one review-boundary fidelity defect and avoids mixing orchestration, retry, UX, or escalation behavior.
- Complexity assessment: Medium
- Risk assessment: Medium
- Blast radius: Narrow
- Registry logic to apply during execution:
  - keep `US-AUTO-28-F1` as `Implemented`
  - move `US-AUTO-54` from `Planned` to `Bundle Drafted` once bundle artifacts are committed
  - after implementation starts, it may move to `In Progress`
  - keep `US-AUTO-54` as the next recommended story until it is merged or explicitly superseded

=== FILE: 06_manual_actions.md ===
## Required Human Actions
1. Create a feature branch for `US-AUTO-54` from current `main`.
2. Save this bundle to `automation/bundle_packs/US-AUTO-54.bundle.md`.
3. Materialize the story bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-54`
4. Validate the materialized bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-54`
5. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so `US-AUTO-54` reflects `Bundle Drafted` or `In Progress`, consistent with the actual execution point.
6. Commit story artifacts before running implementation:
   - bundle pack
   - active bundle files
   - registry update
7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-54`
8. Analyze the pinned run from the fresh current-HEAD run:
   - `automation/scripts/analyze_story_run.sh US-AUTO-54`
9. Review the result and continue through the normal PR flow only if the run corresponds to current HEAD and the scope stayed narrow.

Recommended local file-open commands:
- `open -a "Cursor" automation/bundle_packs/US-AUTO-54.bundle.md`
- `open -a "Cursor" automation/bundles/active/US-AUTO-54`
- `open -a "Cursor" docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Completion Status
- Story selection: complete
- Atomicity check: complete
- Risk and blast-radius assessment: complete
- Registry logic decision: complete
- Bundle pack assembly: complete
- Internal scope synchronization check (`02_file_scope.md` vs `03_master_prompt.md`): complete
- Sanity check for required headings and seven-section contract: complete
- Ready for materialize + validate: yes