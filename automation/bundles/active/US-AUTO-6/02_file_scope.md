# US-AUTO-6: File Scope

## Files Allowed To Change
- `automation/scripts/classify_review_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-6/00_story.md`
- `automation/bundles/active/US-AUTO-6/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-6/02_file_scope.md`
- `automation/bundles/active/US-AUTO-6/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-6/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-6/05_followups.md`
- `automation/bundles/active/US-AUTO-6/06_manual_actions.md`
- `tests/test_review_classification_script.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Scope Notes
- This story adds a thin classification wrapper around the existing AI review artifact.
- It must not introduce auto-fix behavior or alter runtime application code.
