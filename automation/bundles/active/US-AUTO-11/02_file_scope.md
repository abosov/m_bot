# US-AUTO-11: File Scope

## Files Allowed To Change

Primary:
- `automation/run_codex_task.sh`

Tests:
- `tests/test_run_codex_task.py`

Docs:
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

Bundle:
- `automation/bundles/active/US-AUTO-11/00_story.md`
- `automation/bundles/active/US-AUTO-11/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-11/02_file_scope.md`
- `automation/bundles/active/US-AUTO-11/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-11/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-11/05_followups.md`
- `automation/bundles/active/US-AUTO-11/06_manual_actions.md`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/**`
- deploy / infra files
- AI review/classification scripts
- unrelated automation files

## Scope Notes
- Keep patch minimal.
- Do not introduce new framework-level abstractions.
- Do not combine this story with allowed-files enforcement.
