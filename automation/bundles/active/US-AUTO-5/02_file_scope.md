# US-AUTO-5: File Scope

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/**` (only if tiny helper logic is strictly necessary)
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` (only if workflow documentation must be updated)

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Scope Notes
- This story adds a thin AI-review wrapper around existing run artifacts.
- It must not introduce auto-fix behavior.
- It must not alter runtime application code or artifact-generation ownership.
