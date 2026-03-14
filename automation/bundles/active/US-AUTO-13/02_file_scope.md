# US-AUTO-13: File Scope

## Files Allowed To Change
- `automation/scripts/finalize_story.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-13.bundle.md`
- `automation/bundles/active/US-AUTO-13/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Scope Notes
- Keep the script deterministic and CLI-oriented.
- Use `gh` as the default and preferred GitHub integration path.
- Do not mix in scope guard or review gate logic.

