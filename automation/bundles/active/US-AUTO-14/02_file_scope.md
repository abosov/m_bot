# US-AUTO-14: File Scope

## Files Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/run_codex_task.sh`
- `tests/test_allowed_files_guard.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-14.bundle.md`
- `automation/bundles/active/US-AUTO-14/**`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- Keep the guard runtime-only and deterministic.
- Do not mix in diff-size policy or AI review policy.
- Do not refactor unrelated runner behavior.
- Only exact paths and recursive directory patterns ending with `/**` are required in this story.

