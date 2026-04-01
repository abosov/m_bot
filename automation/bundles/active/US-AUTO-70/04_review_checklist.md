## Scope Validation
HARD BLOCK / REJECT if any changed file is outside:
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

HARD BLOCK / REJECT if any implementation change touches:
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- review/gate/analyze scripts
- registry files
- bundle files for other stories

APPROVE only if the diff stays fully inside the allowed pair and clearly targets rerun-preflight stable-review recomputation for the companion-filtered path.

## Functional Validation
HARD BLOCK / REJECT if rerun-preflight still evaluates an unadjusted or stale surface after companion filtering should have narrowed the effective review surface.

HARD BLOCK / REJECT if the implementation introduces fail-open fallback when recomputation inputs are missing, invalid, or ambiguous.

HARD BLOCK / REJECT if the change alters unrelated rerun behavior for non-companion-filtered stories without explicit narrow justification.

APPROVE only if:
- rerun-preflight uses a recomputed effective filtered review surface for the intended path
- unaffected paths remain stable
- failure behavior is deterministic and fail-closed

## Verification
HARD BLOCK / REJECT if `pytest -q tests/test_run_story.py` is not run and reported.

HARD BLOCK / REJECT if new or updated tests do not specifically prove the companion-filtered rerun-preflight path.

Final review outcome must be binary:
- APPROVE
- REJECT

No partial approval.

