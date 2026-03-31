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

