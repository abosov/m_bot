# US-AUTO-12: File Scope

## Files Allowed To Change
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/new_story_bundle.sh`
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `automation/bundle_packs/**`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_story_bundle_scripts.py`
- `automation/bundles/active/US-AUTO-12/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`

## Scope Notes
- Keep parser and validator deterministic.
- Keep bootstrap and execution flow explicit.

