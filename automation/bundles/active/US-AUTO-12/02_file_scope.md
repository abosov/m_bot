# US-AUTO-12: File Scope

## Files Allowed To Change

Primary scripts:
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/new_story_bundle.sh`

Templates / packs:
- `automation/templates/story_bundle_template.md`
- `automation/templates/codex_master_prompt_template.md`
- `automation/templates/followup_prompt_template.md`
- `automation/templates/review_prompt_template.md`
- `automation/templates/pr_description_template.md`
- `automation/bundle_packs/**`

Docs:
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

Tests:
- `tests/test_story_bundle_scripts.py`

Bundle:
- `automation/bundles/active/US-AUTO-12/00_story.md`
- `automation/bundles/active/US-AUTO-12/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-12/02_file_scope.md`
- `automation/bundles/active/US-AUTO-12/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-12/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-12/05_followups.md`
- `automation/bundles/active/US-AUTO-12/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/*` except when strictly needed by docs alignment
- deploy / infra files
- review-gate / finalize-story logic

## Scope Notes
- Keep the pack format simple and deterministic.
- Do not introduce a generalized document engine.
- Do not change actual story execution semantics beyond adding validation gates.
