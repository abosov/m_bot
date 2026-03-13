# US-AUTO-10: File Scope

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-10/*`

## Files Not Allowed To Change
- `backend/**`
- `bots/**`
- `database/**`
- `alembic/**`
- `deployment/**`
- `nginx/**`
- Any product runtime code outside the automation workflow

## Scope Notes
- The runner, its focused tests, and the workflow checklist are the only files needed to enforce the materialization invariant for isolated runs.
- The story must not broaden beyond workflow safety for tracked and regular untracked file materialization back into the primary checkout.
