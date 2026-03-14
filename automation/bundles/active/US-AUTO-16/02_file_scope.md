# US-AUTO-16: File Scope

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-16.bundle.md`
- `automation/bundles/active/US-AUTO-16/00_story.md`
- `automation/bundles/active/US-AUTO-16/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-16/02_file_scope.md`
- `automation/bundles/active/US-AUTO-16/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-16/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-16/05_followups.md`
- `automation/bundles/active/US-AUTO-16/06_manual_actions.md`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/templates/review_prompt_template.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `backend/**`
- `database/**`
- `tests/**`

## Scope Notes
- Prefer adding `automation/scripts/review_gate_story_run.sh` as the main new file.
- Reuse existing review scripts with minimal edits only if required for a stable gate artifact contract.
- Do not integrate with finalize in this story.

