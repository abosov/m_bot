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

