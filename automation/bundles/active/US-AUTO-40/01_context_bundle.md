# Context Bundle — US-AUTO-40

## Source of Truth
- Authoritative reviewed code reality is the actual git diff for the branch under review, normally `origin/main...HEAD`.
- The primary implementation baseline is the current behavior of:
  - `automation/scripts/review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `tests/test_review_story_run.py`
  - `tests/test_review_gate_story_run.py`
  - `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
  - `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Current Code Reality
After US-AUTO-39:
- review/gate records reviewed HEAD;
- gate compares reviewed HEAD with current checkout HEAD;
- mismatch is rejected fail-closed.

Remaining gap:
- review artifacts can still be stale relative to current HEAD diff;
- artifact-declared scope may omit files actually changed in `origin/main...HEAD`;
- review can therefore approve based on a narrative that is not fully faithful to the real branch delta.

## Architectural Intent
The actual branch diff must be the only authoritative technical reality for review.

Review artifacts remain useful, but only if they are faithful to that actual diff.  
The workflow must reject stale, incomplete, or misleading artifacts instead of silently tolerating drift.

This story should enforce fidelity with machine-verifiable checks, not with additional prose alone.

## Risks
- Solving too much and drifting into US-AUTO-41 scope redesign.
- Introducing a second competing source of truth for reviewed scope.
- Weakening existing fail-closed review/gate discipline.
- Adding a brittle check that is overly text-dependent instead of git-state-dependent.

## Acceptance Notes
The implementation should make the following true:
- faithful artifacts can still pass review/gate;
- stale or incomplete artifacts fail deterministically;
- operator-facing messaging explains what drift was detected and how to recover;
- docs reflect the new invariant and rerun/remediation expectation.

## Operational Reminder
Until US-AUTO-37 / US-AUTO-38 are implemented:
- run `git status --short` after `run_story.sh` and `finalize_story.sh`;
- if the only dirt is `M automation/story_change_ledger.jsonl`, restore it immediately.