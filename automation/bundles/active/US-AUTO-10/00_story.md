# US-AUTO-10: Materialize isolated worktree output back to primary repository

## Story ID and Title
- Story ID: `US-AUTO-10`
- Title: `Materialize isolated worktree output back to primary repository`

## Objective
Guarantee that file changes produced by Codex inside the isolated temporary git worktree are materialized into the primary checkout before pytest and artifact collection, or the run fails explicitly.

## Scope
- Add a deterministic post-Codex materialization step to `automation/run_codex_task.sh` for tracked and regular untracked files from the isolated worktree.
- Verify the primary checkout reflects expected isolated-worktree changes before pytest and artifact collection continue.
- Update focused runner tests and the workflow checklist to cover the invariant.

## Non-goals
- No new automation framework or bundle structure changes.
- No product runtime changes outside the automation workflow files listed for this story.

## Dependencies
- `US-AUTO-8` isolated-worktree execution behavior already present in `automation/run_codex_task.sh`.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Current Code Reality
- Codex executes inside a detached temporary worktree created from the primary checkout `HEAD`.
- Pytest and review artifacts are still generated from the primary checkout without first copying isolated-worktree output back.
- The primary checkout is required to be clean before the run starts, which makes deterministic materialization practical.

## Target Architecture
- Keep the existing isolated-worktree execution model.
- Materialize tracked diffs and regular untracked files into the primary checkout immediately after Codex exits.
- Fail the run if isolated changes exist but do not appear in the primary checkout before pytest and artifact collection.

## Allowed Files
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-10/*`

## Forbidden Files
- `backend/**`
- `bots/**`
- `database/**`
- `alembic/**`
- `deployment/**`
- `nginx/**`
- Any product runtime code outside the automation workflow files listed above

## Risks
- Applying isolated tracked diffs into the primary checkout could drift if the primary tree is dirty; mitigation is the existing clean-tree precondition and explicit verification after copy/apply.
- Untracked path handling is intentionally limited to regular files for this story to keep the patch deterministic and minimal.

## Manual Actions
- None beyond running the updated targeted test suite.

## Acceptance Notes
- Tracked changes made in the isolated worktree appear in the primary checkout before pytest runs.
- Regular untracked files created in the isolated worktree appear in the primary checkout and in run artifacts.
- If materialization is expected but missing, the runner exits non-zero instead of reporting success.
