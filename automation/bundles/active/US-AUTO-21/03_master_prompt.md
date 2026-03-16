# US-AUTO-21 PROMPT 1 — Enforce Clean Commit Boundary Before Review Gate

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-21 — Enforce Clean Commit Boundary Before Review Gate

## Goal
Prevent review/gate from evaluating artifact bundles when the current branch contains uncommitted materialized changes and therefore does not represent a commit-consistent review state.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-21.bundle.md`
- `automation/bundles/active/US-AUTO-21/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Current Problem
The runner can validly materialize isolated-worktree changes into the primary checkout.
That leaves the branch dirty until the operator reviews and commits those changes.
The review/gate layer currently does not stop on that dirty state before AI review starts.
As a result, AI review may classify a run against evidence that is not aligned with committed branch state, causing false rejects.

## Implementation Requirements
1. Add a review-stage precheck that detects whether the current branch working tree is dirty before review/gate proceeds.
2. Fail fast before AI review/classification starts when review evidence is not commit-consistent.
3. Make `review_story_run.sh` surface whether the latest run is review-safe or blocked by dirty working tree.
4. Make `review_gate_story_run.sh` refuse to proceed when the current branch is dirty.
5. Keep behavior fail-closed.
6. Do not modify `automation/run_codex_task.sh`.
7. Do not add auto-commit behavior.

## Operator UX Requirements
When blocked, print a clear operator-facing message that explains:
- uncommitted materialized changes exist in the current branch
- review/gate is blocked because branch state is not commit-consistent
- inspect and commit the changes first
- if a fresh run is needed for the newly committed state, rerun `automation/scripts/run_story.sh <STORY_ID>`
- then rerun `automation/scripts/review_gate_story_run.sh <STORY_ID>`

## Suggested UX Shape
Example review summary block:
Review safety: BLOCKED
Reason: working tree contains uncommitted materialized changes
Next step:
1. inspect changes
2. commit changes
3. if needed, rerun automation/scripts/run_story.sh US-AUTO-21
4. rerun automation/scripts/review_gate_story_run.sh US-AUTO-21

Example gate failure block:
ERROR: review gate blocked for 'US-AUTO-21'
Reason: current branch has uncommitted changes; review artifacts would not match committed state
Required action:
- inspect and commit the materialized changes
- if needed, rerun automation/scripts/run_story.sh US-AUTO-21
- rerun automation/scripts/review_gate_story_run.sh US-AUTO-21

## Testing
Add or update focused tests that verify:
- clean working tree allows normal review/gate flow
- dirty working tree blocks `review_story_run.sh` with explicit status/output
- dirty working tree blocks `review_gate_story_run.sh` before AI review starts
- operator-facing message is actionable and stable

## Documentation
Update workflow docs/checklists to describe the clean commit boundary rule before review/gate.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

