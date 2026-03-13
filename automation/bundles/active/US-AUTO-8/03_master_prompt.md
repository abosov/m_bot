# US-AUTO-8 PROMPT 1 — Isolated Codex runs via git worktree

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-8 — Isolated Codex runs via git worktree

## ctive
Change the implementation execution model so Codex runs inside an isolated temporary git worktree instead of directly mutating the operator's primary working tree.

## Problem to solve

Current implementation runs operate in the primary repo working tree.

That creates workflow instability:
- failed runs leave dirty state
- reruns depend on manual cleanup
- operator state and run state get mixed
- review reliability suffers when execution is not isolated

## Required outcome

Implement isolated run execution using git worktree.

At minimum:

- create a temporary worktree from current branch HEAD
- run Codex inside that worktree
- preserve the normal artifact output structure
- record isolated-run metadata in manifest
- clean up temporary worktree on success and failure

## Before implementing
1. Identify the exact files to modify.
2. Identify the exact worktree lifecycle.
3. State what path will be used for the temporary worktree.
4. State how cleanup will be guaranteed.
5. State which files/layers must not be changed.

## Files allowed to change
- automation/run_codex_task.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- tests/test_run_codex_task.py
- automation/bundles/active/US-AUTO-8/*

## Files not allowed to change
- backend/**
- bots/**
- database/**
- alembic/**
- deployment/**
- nginx/**
- any product runtime code outside automation workflow

## Implementation rules
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- no new files unless strictly necessary
- do not touch files outside allowed scope

## Suggested direction

Use `git worktree add --detach` or an equivalent minimal approach.

Keep these principles:

- execution environment is isolated
- operator working tree remains untouched
- artifact collection remains in the main automation run directory
- cleanup is explicit and reliable

## Testing

Add or update tests to prove:

1. isolated worktree is created for the run
2. Codex execution uses the isolated worktree path
3. operator working tree is not directly modified by the run process
4. manifest contains isolated-run metadata
5. cleanup works in success and failure paths

## Documentation

Update workflow documentation/checklist if assumptions change.

## Output format

Return:

1. implementation summary
2. files changed
3. tests run
4. residual risks
