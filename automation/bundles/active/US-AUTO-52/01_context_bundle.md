# Context Bundle — US-AUTO-52

## Source of Truth
Primary implementation and verification files for this story are:
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_analyze_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
The current pipeline already demonstrates the important architectural fact: manual finish can produce a continuation-ready path for a previously blocked non-converging rerun. That removes the older “impossible to continue review after manual finish” blocker in principle. The remaining defect is narrower and contractual: the continuation predicate accepts a broader ancestry relationship than intended. Review evidence also shows stale verification artifacts relative to the latest HEAD, which is expected once a manual-finish commit advances the branch after the reviewed run. The corrective story must not re-open the solved part of the problem; it must only tighten the acceptance boundary for continuation.

## Architectural Intent
The pipeline must remain deterministic, committed-HEAD-based, and fail-closed. Manual finish is not a generic stale-run escape hatch. It is a tightly scoped recovery path for one specific committed case: the exact manual-finish commit that completes the previously blocked run. The architecture should preserve these invariants:
- review stages never silently reinterpret stale evidence,
- continuation does not follow general ancestry,
- exact-case recovery is allowed only when run evidence explicitly supports it,
- all other cases reject with deterministic stale-run behavior.

## Risks
- Over-correcting could disable the valid exact-case continuation path that US-AUTO-51 proved.
- Under-correcting could leave ancestor-based continuation in place and keep the contract too permissive.
- Partial fixes in only one script could create inconsistent analyze/classify/gate outcomes.
- Broad documentation edits could drift from the narrow implementation intent.

## Acceptance Notes
A valid implementation for this story should show:
- exact-case continuation allowed,
- descendant-of-manual-finish continuation blocked,
- ancestor-based continuation blocked,
- no broadening of scope into unrelated review or rerun flow,
- deterministic pinned-run review behavior preserved.

