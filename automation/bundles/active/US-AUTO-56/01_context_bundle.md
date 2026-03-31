## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality
The epic registry marks US-AUTO-56 as the next recommended story after US-AUTO-55. The fail-closed workflow boundary is already stable:
- ordinary review after an implementation commit requires a fresh committed-head rerun
- `run -> commit -> review` is not a valid normal path
- manual-finish continuation is the only explicit exception after `blocked_non_converging_rerun`
- when manual-finish continuation is active, rerun must not happen again until manual finish is complete

The remaining gap is not policy correctness; it is explicit operator-facing stage guidance. Current outputs can still leave room for confusion about whether review-stage is allowed now, whether commit/discard must happen first, and whether rerun is forbidden under manual-finish continuation.

## Architectural Intent
Keep the pipeline fail-closed and deterministic while reducing operator ambiguity.

The story must:
- surface existing workflow invariants at the exact post-run decision points
- make the next safe step obvious
- make forbidden actions explicit
- avoid adding new orchestration or broad UX behavior

The guidance should act as a thin interpretation layer over existing rules, not as a new workflow engine.

## Risks
- accidental semantic changes disguised as messaging improvements
- expanding from stage guidance into loop prevention, retry budget, or telemetry
- inconsistent phrasing between `run_story.sh` and `analyze_story_run.sh`
- tests validating prose too loosely or too rigidly

## Acceptance Notes
A correct implementation keeps all existing boundaries intact and only makes them explicit:
- normal rerun/review path guidance remains committed-head first
- manual-finish continuation remains a narrow exception with rerun prohibition
- dirty tree remains a hard stop for review-stage eligibility until resolved
- no other scripts become part of scope

