# US-AUTO-21: Context Bundle

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Current Code Reality
- Story execution already uses isolated worktree execution and materialization into the primary checkout.
- Review artifacts are already derived from commit-based evidence, not just from transient working-tree state.
- The remaining workflow gap is at review/gate time: the operator can hold valid materialized changes locally without committing them, and the review layer currently does not fail fast on that inconsistency.
- This creates a false-reject class: artifact integrity / workflow compliance can fail even though the implementation itself is acceptable.

## Architectural Intent
- Keep commit-based review as the source of truth.
- Enforce a clean commit boundary before review/gate.
- Prefer explicit operator control over hidden automation.
- Fail fast before AI review/classification starts when branch state is not review-safe.

## Risks
- Overblocking review if the check is broader than intended.
- Underblocking review if dirty-tree detection is incomplete or inconsistent between scripts.
- Confusing operator guidance if the script implies rerunning Codex is always required when only a commit is needed.

## Acceptance Notes
- The failure message must be explicit and actionable.
- The blocked state must be visible in both `review_story_run.sh` and `review_gate_story_run.sh`.
- The implementation should stay minimal and avoid redesigning runner behavior.

