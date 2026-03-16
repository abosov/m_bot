# US-AUTO-21: Enforce Clean Commit Boundary Before Review Gate

## Story ID and Title
- Story ID: `US-AUTO-21`
- Title: `Enforce Clean Commit Boundary Before Review Gate`

## Objective
Prevent review and gate from running against a branch state that contains uncommitted materialized changes, so AI review always evaluates commit-consistent evidence.

## Scope
- Add an explicit clean-commit-boundary rule before review/gate execution.
- Detect when the current branch working tree is dirty before review/gate starts.
- Block review/gate before AI review and classification begin if the reviewed branch state is not commit-consistent.
- Return a clear operator-facing error explaining what to do next.
- Update docs and tests for the new workflow rule.

## Non-goals
- No automatic git commit creation by automation.
- No redesign of review/gate to operate on arbitrary working-tree snapshots instead of commit-based evidence.
- No changes to business logic of Codex implementation or story execution semantics outside review-boundary enforcement.
- No redesign of review artifact generation in `automation/run_codex_task.sh`.

## Dependencies
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- existing run artifacts under `automation/runs/<STORY_ID>/...`

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Current Code Reality
- `automation/run_codex_task.sh` already enforces a clean tree before execution, runs Codex in an isolated worktree, materializes resulting changes into the primary checkout, and builds review artifacts from a commit-range base.
- After materialization, the current branch can legitimately contain uncommitted changes in the primary checkout.
- `review_story_run.sh` currently summarizes the latest run but does not enforce a clean commit boundary before review.
- `review_gate_story_run.sh` currently proceeds into review/classification flow without a fail-fast dirty-tree precheck.
- This can produce false review-gate rejections because review evidence is interpreted as if it reflected a committed branch state while the operator is still holding uncommitted materialized changes.

## Target Outcome
- Review and gate fail fast when the current branch working tree is dirty.
- The operator gets explicit guidance on how to restore a review-safe state.
- AI review and classification never start from a non-committed branch state.
- Commit-based review remains the source of truth.

## Acceptance Notes
- Fail closed if branch state is not review-safe.
- The console message must clearly explain that uncommitted materialized changes must be inspected and committed before review/gate proceeds.
- The guidance may suggest rerunning `automation/scripts/run_story.sh <STORY_ID>` only if a fresh run is desired for the newly committed state.
- The normal clean-tree path must remain unchanged.

