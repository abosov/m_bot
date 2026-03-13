# US-AUTO-7 File Scope

## Files allowed to change

Primary:
- automation/run_codex_task.sh
- automation/scripts/review_story_run.sh

Documentation / bundle:
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- automation/bundles/active/US-AUTO-7/00_story.md
- automation/bundles/active/US-AUTO-7/01_context_bundle.md
- automation/bundles/active/US-AUTO-7/02_file_scope.md
- automation/bundles/active/US-AUTO-7/03_master_prompt.md
- automation/bundles/active/US-AUTO-7/04_review_checklist.md
- automation/bundles/active/US-AUTO-7/05_followups.md
- automation/bundles/active/US-AUTO-7/06_manual_actions.md

Tests:
- tests/test_run_codex_task.py
- tests/test_review_story_run.py

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

- automation/run_codex_task.sh
- latest story run artifacts under automation/runs/<STORY_ID>/<RUN_ID>/
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md

## Notes

Keep patch minimal.

Do not redesign the whole pipeline.
Do not change product runtime behavior.
Do not add unrelated refactors.

The goal is to make review evidence stable for committed story diffs.
