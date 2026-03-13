# US-AUTO-4: File Scope

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/templates/**`
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Scope Notes
- This story optimizes runner context selection only.
- It must not redesign the bundle structure.
- It must not alter runtime product code.
