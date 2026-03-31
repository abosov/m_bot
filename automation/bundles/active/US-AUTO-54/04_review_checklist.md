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

