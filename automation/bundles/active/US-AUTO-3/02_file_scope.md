# US-AUTO-3: File Scope

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/**` (only if tiny helper logic is strictly necessary)
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` (only if review-launcher usage must be documented)

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Scope Notes
- This story adds a thin wrapper around existing run artifacts.
- The wrapper must resolve STORY_ID -> latest run directory -> review artifacts.
- Artifact generation must remain owned by `automation/run_codex_task.sh`.
- The launcher must not introduce auto-fix logic, PR automation, or runtime code changes.
