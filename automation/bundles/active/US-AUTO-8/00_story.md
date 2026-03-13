# US-AUTO-8 — Isolated Codex runs via git worktree

## Problem

Current Codex implementation runs modify the operator's primary working tree directly.

That creates several workflow risks:

- failed or partial runs leave the main repository dirty
- reruns depend on manual cleanup
- review may accidentally happen against a mixed or partially edited state
- auditability is weaker because run state is not isolated from operator state

## Goal

Run Codex implementation passes in an isolated temporary git worktree instead of directly in the operator's primary working tree.

## Desired behavior

When a story run starts, the automation workflow should:

1. create a temporary worktree from the current branch HEAD
2. execute the Codex implementation run inside that isolated worktree
3. collect run artifacts in the normal automaon run directory
4. leave the operator's primary working tree untouched
5. clean up the temporary worktree on success and failure

## Scope

Allowed:

- update automation run workflow
- add helper logic for worktree lifecycle if needed
- update run manifest fields if needed
- add/update tests for isolated run behavior
- update workflow documentation/checklists
- update active story bundle for US-AUTO-8

Not allowed:

- no product runtime changes
- no DB/schema changes
- no deployment changes
- no unrelated refactor

## Source of truth

- `automation/run_codex_task.sh`
- run artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Acceptance criteria

1. Codex implementation run does not modify the operator's primary working tree directly.
2. A temporary worktree is created from the current branch HEAD for the run.
3. Run artifacts are still written under `automation/runs/<STORY_ID>/<RUN_ID>/`.
4. The manifest clearly records isolated-run metadata such as worktree path and source HEAD.
5. Temporary worktree cleanup succeeds on success and failure paths.
6. Failure paths do not leave orphaned worktree state in normal cases.
7. Tests cover isolated worktree lifecycle and cleanup behavior.

## Notes

This is an architectural hardening story for the AI-dev pipeline.

The main objective is to make implementation runs reproducible, isolated, and safe to rerun.
