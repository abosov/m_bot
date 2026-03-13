# US-AUTO-8 File Scope

## Files allowed to change

Primary:
- automation/run_codex_task.sh

Optional helper if strictly needed:
- automation/scripts/**

Documentation / bundle:
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- automation/bundles/active/US-AUTO-8/00_story.md
- automation/bundles/active/US-AUTO-8/01_context_bundle.md
- automation/bundles/active/US-AUTO-8/02_file_scope.md
- automation/bundles/active/US-AUTO-8/03_master_prompt.md
- automation/bundles/active/US-AUTO-8/04_review_checklist.md
- automation/bundles/active/US-AUTO-8/05_followups.md
- automation/bundles/active/US-AUTO-8/06_manual_actions.md

Tests:
- tests/test_run_codex_task.py

## Files explicitly not allowed to change

- backend/**
- bots/**
- database/**
- alembic/**
- docker/**
- deployment/**
- nginx/**
- frontend runtime code
- any product/business logic outside automation workflow

## Source of truth

- `automation/run_codex_task.sh`
- run artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Notes

Keep patch minimal.

Do not redesign the whole pipeline.
Do not change product runtime behavior.
Do not add unrelated refactors.

The goal is isolated implementation execution via temporary git worktree.
