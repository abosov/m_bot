# US-AUTO-2: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/**` (only if small helper logic is needed)
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` (only if documentation of the launcher is required)

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/templates/**`
- `backend/**`
- `frontend/**`
- `.github/**`
- deployment / infrastructure files
- database migrations

## Scope Notes
- The story adds a **thin launcher wrapper** around the existing Codex runner.
- The launcher must only resolve STORY_ID → bundle → master prompt.
- All execution logic must remain inside `automation/run_codex_task.sh`.
- The launcher must not introduce a new pipeline or duplicate existing logic.
