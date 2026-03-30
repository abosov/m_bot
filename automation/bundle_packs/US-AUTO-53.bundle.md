# Story Bundle Pack
Story-ID: US-AUTO-53
Version: 1

=== FILE: 00_story.md ===
## Story ID and Title

**Story ID:** US-AUTO-53  
**Title:** Committed-HEAD diff.patch review fidelity

## Objective

Restore a strict fail-closed review artifact fidelity contract so `review_gate_story_run.sh` does not reject a clean committed-HEAD run with `review_diff_patch_mismatch` when the pinned run evidence was generated from the same committed implementation state.

## Scope

This story is limited to the review-artifact fidelity boundary for `diff.patch` on committed HEAD.

In scope:
- deterministic generation and comparison of `diff.patch` for downstream review on committed HEAD
- normalization rules required to keep the diff comparison stable
- focused regression coverage for committed-HEAD diff fidelity
- conservative run-analysis messaging if needed to preserve the fail-closed contract
- conservative registry update for US-AUTO-53

## Non-goals

- no changes to escalation policy semantics
- no changes to escalation artifact schema beyond what already exists
- no weakening of review gate strictness
- no manual-finish UX redesign
- no retry orchestration, caching, or reuse expansion
- no broad changes across unrelated pipeline stages
- no test contract rewrites to mask the defect

## Dependencies

- US-AUTO-45 — deterministic review gate artifact reuse
- US-AUTO-46 — review operates strictly on committed HEAD
- US-AUTO-49 — scope validation ignores committed active-story bundle artifacts
- US-AUTO-50 — AI review structured output and review artifact fidelity stabilization
- US-AUTO-52 — strict manual-finish continuation contract

## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality

`US-AUTO-28-F1` was resumed on a clean branch from `origin/main`, passed story-local tests on committed HEAD, and successfully produced fresh run, analyze, and AI review evidence on clean committed state. Despite that, `review_gate_story_run.sh` still rejected the pinned run with `review_diff_patch_mismatch`, even though committed HEAD consistency matched.

That narrows the remaining blocker to downstream review-artifact fidelity around `diff.patch` comparison on committed HEAD.

## Target Outcome

After this story:
- a clean committed-HEAD rerun produces a `diff.patch` artifact that remains valid for downstream gate comparison against the same committed implementation state
- `review_gate_story_run.sh` rejects only true mismatches, not formatting drift or wrong-target comparison
- the review pipeline remains fail-closed for stale, mismatched, or cross-commit evidence
- `US-AUTO-28-F1` can be resumed only after this follow-up is merged

## Atomic Task Isolation Contract

This story must solve exactly one problem: committed-HEAD `diff.patch` fidelity at the review boundary.

Allowed:
- fix the generation and comparison contract for review diff evidence
- add narrow regression coverage for the exact mismatch class
- update analysis messaging only when necessary to preserve the same strict boundary

Forbidden:
- broad manual-finish workflow redesign
- operator UX expansion
- escalation-policy changes
- cache, reuse, or retry features
- scope widening into unrelated review artifacts or orchestration layers

If implementation pressure expands beyond committed-HEAD diff fidelity, stop and split a follow-up story instead of widening this one.

## Risks

- accidentally weakening the gate so true stale evidence passes
- fixing the symptom in tests while leaving runtime behavior inconsistent
- scope drift into generic manual-finish or review recovery UX

## Manual Actions

- materialize the bundle pack into active bundle files
- validate the bundle before any code changes
- update the registry conservatively to add US-AUTO-53 and make it the next recommended story
- create a dedicated feature branch before running automation
- commit story artifacts before `run_story.sh`
- after implementation commit, rerun the story and analyze the fresh run directory
- do not reuse any pinned `AUTOMATION_RUN_DIR` after a new commit

## Acceptance Notes

Acceptance requires all of the following:
- committed-HEAD review diff fidelity is deterministic
- true stale or mismatched diff evidence still fails closed
- focused tests cover the exact mismatch and non-mismatch cases
- the story remains narrow and does not redesign manual-finish workflow
- downstream evidence remains consistent with the invariant `run -> commit -> rerun -> review`
- `US-AUTO-28-F1` remains blocked until this follow-up is merged, then becomes resumable

=== FILE: 01_context_bundle.md ===
## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality

The registry records `US-AUTO-28-F1` as blocked by a downstream review-artifact fidelity issue, not by an implementation defect in escalation validation. On clean committed HEAD, fresh run, analyze, and AI review evidence was successfully produced, yet `review_gate_story_run.sh` rejected merge with `review_diff_patch_mismatch` while committed HEAD consistency still matched.

This narrows the defect to the review boundary: the pinned run `diff.patch` and the gate’s current comparison target are not being evaluated through exactly the same committed implementation lens.

## Architectural Intent

The pipeline must remain strict:
- review stages operate only on committed HEAD
- stale or mismatched evidence must fail closed
- downstream review must compare the exact implementation delta represented by the pinned run
- deterministic recovery means rerun on the new committed state, not bypass the gate

This story tightens the artifact fidelity contract rather than softening enforcement.

## Risks

- normalizing the wrong diff target can hide true divergence
- relaxing artifact checks can regress review-boundary safety established by US-AUTO-45, US-AUTO-46, and US-AUTO-52
- mixing in operator UX or generic recovery logic will widen scope and reintroduce cycle risk

## Acceptance Notes

- use exact committed-HEAD evidence as the review comparison baseline
- preserve fail-closed rejection for real stale evidence
- add regression tests for the committed-match case and a true-mismatch case
- do not modify unrelated escalation or orchestration behavior

=== FILE: 02_file_scope.md ===
## Files Allowed To Change

- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

- `automation/scripts/run_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- any application or runtime files outside the automation review boundary
- any tests unrelated to run diff, analyze messaging, or review gate fidelity

## Scope Notes

Allowed change types:
- deterministic diff generation and comparison fixes
- narrow fail-closed analysis messaging updates, if required
- focused regression tests for the exact committed-HEAD mismatch contract
- conservative registry update to register US-AUTO-53 and adjust next recommended ordering

Forbidden change types:
- escalation feature changes
- orchestration redesign
- manual-finish UX expansion
- broad refactors
- weakening stale-evidence rejection
- changing external test contracts to hide the defect

Hard anti-drift rule:
If the solution appears to require changes outside the allowed file list, stop and record a follow-up instead of widening this story.

=== FILE: 03_master_prompt.md ===
## Role

You are the implementation engineer for the US-AUTO automation pipeline. Work only within the narrow review-artifact fidelity boundary defined for US-AUTO-53.

## Goal

Fix the committed-HEAD `diff.patch` fidelity defect so downstream review compares the exact committed implementation delta represented by the pinned run, without weakening any fail-closed review safeguards.

## Source of Truth

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`

## Files Allowed To Change

- `automation/run_codex_task.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_codex_task.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

- `automation/scripts/run_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- any application or runtime files outside the automation review boundary
- any unrelated tests

## Atomic Task Isolation Contract

Implement exactly one thing: deterministic committed-HEAD `diff.patch` fidelity for downstream review.

Do not:
- redesign manual-finish flow
- change escalation semantics
- add cache, retry, or orchestration features
- weaken fail-closed gate behavior
- broaden scope to unrelated review artifacts

If the defect cannot be fixed within the allowed files and this narrow boundary, stop and document a focused follow-up instead of widening the story.

## Execution Gate

Before changing code:
1. inspect the current committed behavior in the allowed files only
2. confirm the defect is specifically about committed-HEAD diff comparison, not stale workspace-only divergence
3. keep the external contract strict: true mismatches must still reject

During implementation:
- preserve committed-HEAD boundary semantics from US-AUTO-46
- preserve strict continuation semantics from US-AUTO-52
- preserve story-artifact filtering behavior already established downstream of US-AUTO-49 and US-AUTO-50 unless the exact committed diff target must be normalized further

## Implementation Requirements

- make the gate compare against the exact committed implementation diff intended by the pinned run
- ensure normalization is deterministic if formatting drift or target-selection drift exists
- keep stale or cross-commit evidence fail-closed
- update analyze messaging only if needed to explain the exact reject reason more precisely
- add focused regression tests that prove:
  - committed-match case passes the fidelity check
  - true mismatch still rejects
  - no scope widening into unrelated pipeline stages

## Verification Requirements

Run only the minimal relevant verification needed for this story:
- targeted tests for `run_codex_task`
- targeted tests for `review_gate_story_run`
- targeted tests for `analyze_story_run` if messaging changes
- any story-local automation checks needed to validate committed-HEAD diff fidelity

Do not claim success unless focused verification demonstrates both:
- exact committed-match acceptance
- true mismatch rejection

## Output

Produce:
- minimal code changes within allowed files
- focused regression tests
- conservative registry update for US-AUTO-53
- no unrelated edits

If blocked, report the exact narrow blocker and stop without workaround.

=== FILE: 04_review_checklist.md ===
## Scope Validation

APPROVE only if:
- all modified files are listed in `02_file_scope.md`
- the implementation remains limited to committed-HEAD `diff.patch` fidelity
- no escalation semantics or unrelated orchestration logic changed
- registry update is conservative and limited to adding or updating the relevant story records

REJECT if:
- any out-of-scope file changed
- the story broadens into manual-finish UX, retry logic, or generic review recovery
- fail-closed review strictness is weakened
- tests were changed to hide behavior rather than validate the corrected contract

## Functional Validation

APPROVE only if:
- the committed-match diff case is handled deterministically
- `review_diff_patch_mismatch` remains available for true mismatches
- downstream review still operates on committed HEAD only
- no workaround bypasses gate enforcement
- `US-AUTO-28-F1` is unblocked only by merging this follow-up, not by manual override

REJECT if:
- stale or mismatched evidence can now pass
- the fix depends on workspace-only state
- the implementation changes escalation behavior
- the solution relies on skipping gate or treating mismatches as warnings

## Verification

Required evidence:
- targeted green tests for `tests/test_run_codex_task.py`
- targeted green tests for `tests/test_review_gate_story_run.py`
- targeted green tests for `tests/test_analyze_story_run.py` if touched
- concise proof that committed-match and true-mismatch scenarios are both covered

HARD BLOCK:
- reject if verification is missing
- reject if test coverage does not include both pass and fail fidelity paths
- reject if committed-HEAD boundary semantics regress
- reject if the solution depends on reusing a stale run directory after a new commit

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue

1. Resume `US-AUTO-28-F1` only after US-AUTO-53 is merged and `main` is updated locally. Re-run the story from a fresh committed state and use a new run directory.
2. If committed-HEAD diff fidelity still exposes another distinct review-boundary defect, split a new narrow follow-up rather than widening US-AUTO-53.
3. Revisit P2 workflow optimization stories `US-AUTO-29`, `US-AUTO-30`, and `US-AUTO-31` only after the current P1 blocker is cleared.

## Iteration Notes

- This story is intentionally narrower than manual-finish workflow recovery.
- The correct architectural response is to fix the diff comparison contract, not to bypass or soften the gate.
- Registry logic after this bundle:
  - add `US-AUTO-53` as a new P1 follow-up tied to `US-AUTO-28-F1`
  - set `US-AUTO-53` as the next recommended story
  - keep `US-AUTO-28-F1` blocked until this follow-up is implemented and merged
- Estimated delivery profile:
  - Complexity: Medium
  - Risk: Medium
  - Blast Radius: Narrow
- No further split is required at bundle stage because the defect is already isolated to review diff fidelity.
- Main regression risk: accidentally converting true mismatches into false passes.

=== FILE: 06_manual_actions.md ===
## Required Human Actions

1. Save this bundle pack to `automation/bundle_packs/US-AUTO-53.bundle.md`.
2. From the repository root on the local machine, run:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-53`
   - `automation/scripts/validate_story_bundle.sh US-AUTO-53`
3. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` conservatively so:
   - `US-AUTO-53` is registered as a new P1 follow-up for the committed-HEAD `review_diff_patch_mismatch` blocker
   - `US-AUTO-53` becomes the first next recommended story
   - `US-AUTO-28-F1` remains blocked until US-AUTO-53 is merged
4. Create a dedicated feature branch from updated `main`.
5. Commit the story artifacts before running automation.
6. Run the story on the feature branch:
   - `automation/scripts/run_story.sh US-AUTO-53`
7. After implementation commit, rerun the story on the new committed HEAD and then analyze the fresh run:
   - `automation/scripts/analyze_story_run.sh US-AUTO-53`
8. Do not reuse any previous `AUTOMATION_RUN_DIR` after a new commit.
9. Only proceed to review and gate using evidence from the latest rerun aligned to current HEAD.

## Completion Status

- Bundle drafted: complete
- Materialize: pending
- Validate: pending
- Registry update: pending
- Branch creation: complete
- Story-artifact commit: pending
- Implementation: pending
- Fresh rerun on committed HEAD: pending
- Analyze latest run: pending
- Review and gate: pending
- Merge: pending