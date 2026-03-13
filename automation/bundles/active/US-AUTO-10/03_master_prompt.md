# US-AUTO-10 PROMPT 1 — Materialize isolated worktree output back to primary repository

## ROLE
You are the Zumbot workflow automation engineer working under the repository CODEX Operating System.

## TASK
Fix the isolated-run workflow so Codex output produced inside the temporary git worktree is materialized back into the primary repository before pytest and artifact collection.

This story is NOT about adding another layer of abstraction.
This story is about enforcing a strict workflow invariant:

If Codex changes files inside the isolated worktree, those changes must either:
1. appear in the primary repository working tree before pytest/artifact collection, or
2. cause the run to fail explicitly.

Silent success is forbidden.

## MANDATORY CONTEXT
Read and follow:
- docs/90_codex/CODEX_OPERATING_SYSTEM.md
- docs/90_codex/PROJECT_CONTEXT.md
- docs/90_codex/REPOSITORY_MAP.md
- docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- automation/bundles/active/US-AUTO-10/00_story.md
- automation/bundles/active/US-AUTO-10/01_context_bundle.md
- automation/bundles/active/US-AUTO-10/02_file_scope.md

## PROBLEM
US-AUTO-8 successfully isolated Codex execution in a temporary git worktree.

But the current runner still has a critical workflow defect:

- Codex can modify files inside the isolated worktree
- the runner may still collect review artifacts from the primary checkout
- the isolated worktree is then cleaned up
- the primary repository remains unchanged
- the run still ends with "Done"

This creates a false-positive successful run.

This defect has already been observed in practice:
- codex_last_message described real implementation changes
- git status in the primary repo stayed clean
- changed_files.txt did not include implementation files
- the actual code changes disappeared with worktree cleanup

## GOAL
Implement a minimal, reliable materialization step in the runner so that isolated worktree output becomes visible in the primary repository before pytest and artifact collection.

The final behavior must guarantee:
1. tracked file changes from the isolated worktree are applied into the primary checkout
2. untracked files created by Codex inside the isolated worktree are copied into the primary checkout
3. pytest runs against the materialized primary checkout state
4. git artifacts are collected from the primary checkout after materialization
5. if isolated worktree changes exist but do not appear in the primary checkout, the run must fail explicitly instead of reporting success

## NON-GOALS
Do not:
- create a new automation framework
- add unrelated refactors
- change bundle structure
- touch product runtime code outside the automation workflow
- silently ignore materialization failure
- solve future edge cases beyond normal tracked files and regular untracked files unless required for this story

## SOURCE OF TRUTH
- automation/run_codex_task.sh
- tests/test_run_codex_task.py
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md

## FILES ALLOWED TO CHANGE
- automation/run_codex_task.sh
- tests/test_run_codex_task.py
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- automation/bundles/active/US-AUTO-10/*

## FILES NOT ALLOWED TO CHANGE
- backend/**
- bots/**
- database/**
- alembic/**
- deployment/**
- nginx/**
- any product runtime code outside automation workflow

## REQUIRED IMPLEMENTATION DIRECTION
Use the existing isolated worktree model.

After Codex exits, but before pytest and artifact collection:
- detect tracked changes in the isolated worktree relative to the source HEAD
- apply those tracked changes into the primary repository in a deterministic way
- materialize regular untracked files from the isolated worktree into the primary repository
- verify that materialization actually occurred when isolated changes exist
- fail the run if materialization was expected but did not reach the primary checkout

The primary repository is already required to be clean before the run starts.
Use that precondition to keep the implementation simple and deterministic.

## REQUIRED TEST COVERAGE
Update tests to prove all of the following:

1. tracked changes made by Codex in the isolated worktree appear in the primary repository after the run
2. untracked files created in the isolated worktree appear in the primary repository after the run
3. the materialization step also runs when Codex exits non-zero but still produced file changes
4. the runner does not silently report success when isolated changes exist but are not materialized
5. artifact collection and/or manifest behavior stays aligned with the materialized primary checkout state

Prefer focused tests in:
- tests/test_run_codex_task.py

## DOCUMENTATION
Update docs/90_codex/STORY_EXECUTION_CHECKLIST.md only as needed to reflect the new guaranteed workflow behavior.

## IMPLEMENTATION RULES
- minimal patch only
- no unrelated refactor
- no formatting-only edits
- do not invent new files unless strictly necessary
- preserve current workflow shape as much as possible
- make the workflow safer, not broader

## OUTPUT FORMAT
Return:
1. changed files summary
2. rationale
3. test results
4. risks/follow-ups
5. final diff