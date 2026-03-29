# US-AUTO-51 — Review Checklist

## Scope Validation
- [ ] Only downstream continuation files changed: analyze / classify / gate, their direct tests, and minimal docs/registry updates.
- [ ] No changes were made to `run_story.sh`, `run_codex_task.sh`, or `ai_review_story_run.sh`.
- [ ] No changes were made outside the explicit allowed file list.
- [ ] The patch does not absorb `US-AUTO-28-F1` implementation work.

## Functional Validation
- [ ] Manual-finish continuation is allowed only for the exact confirmed non-converging rerun case.
- [ ] Generic stale-run mismatch remains fail-closed.
- [ ] Analyze messaging remains stable before and after downstream artifacts exist.
- [ ] Classification can continue on committed manual-finish `HEAD`.
- [ ] Gate can continue on committed manual-finish `HEAD`.
- [ ] Gate still enforces authoritative diff fidelity against current `HEAD`.
- [ ] Clean working tree remains mandatory.

## Verification
- [ ] `pytest -q tests/test_analyze_story_run.py`
- [ ] `pytest -q tests/test_classify_review_story_run.py`
- [ ] `pytest -q tests/test_review_gate_story_run.py`
- [ ] Manual-finish continuation case passes with pinned artifacts.
- [ ] Generic stale-run mismatch case still rejects deterministically.
- [ ] Registry and checklist docs updated consistently.

## HARD BLOCK
- [ ] REJECT if the stale-run exception becomes broader than the exact manual-finish continuation case.
- [ ] REJECT if gate fidelity checks are weakened or bypassed.
- [ ] REJECT if upstream run or AI review behavior is changed.
- [ ] REJECT if analyze text says continuation is allowed but classify/gate still reject the same exact case.
- [ ] REJECT if the patch relies on silent artifact regeneration or hidden reruns.

