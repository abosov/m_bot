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

