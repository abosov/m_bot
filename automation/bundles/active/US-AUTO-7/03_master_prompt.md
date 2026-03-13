# US-AUTO-7 PROMPT 1 — Stable review evidence from commit range

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-7 — Stable review evidence from commit range

## Objective
Fix the review evidence generation workflow so that review artifacts remain valid when the story changes are already committed and the working tree is clean.

## Problem to solve
Current workflow evidence is generated from the post-run working tree.
That causes false review blockers after a story has already been committed, because the latest run may show:

- empty `changed_files.txt`
- empty `diff.patch`
- `changed_files_detected: no`

even though the branch really contains committed story changes.

## Required outcome
Make review evidence stable and reproducible from a commit-range based diff source.

At minimum:

- review artifacts must reflect actual branch changes relative to the review base
- this must still work when the working tree is clean
- `changed_files.txt`, `diff.patch`, `manifest.md`, and review bundle sections must stay consistent

## Before implementing
1. Identify the exact fil to modify.
2. Identify the exact source of truth for review evidence.
3. State clearly which diff source will be used.
4. State which files/layers must not be changed.

## Files allowed to change
- automation/run_codex_task.sh
- automation/scripts/review_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- tests/test_run_codex_task.py
- tests/test_review_story_run.py
- automation/bundles/active/US-AUTO-7/*

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
Prefer deriving review evidence from a stable git diff source such as the story branch compared to the review base, instead of relying only on uncommitted working tree changes.

If needed, clearly document which base is used for the diff.

## Testing
Add or update tests to prove:

1. committed story changes are still visible in review evidence when working tree is clean
2. `changed_files.txt` and `diff.patch` are populated from the stable diff source
3. manifest/reporting does not incorrectly claim no changed files
4. review bundle output is consistent with the same diff source

## Documentation
Update workflow documentation/checklist if behavior or assumptions change.

## Output format
Return:

1. implementation summary
2. files changed
3. tests run
4. residual risks
