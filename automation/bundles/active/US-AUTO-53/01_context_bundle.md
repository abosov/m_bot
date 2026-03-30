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

