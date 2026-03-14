# US-AUTO-16: File Scope

## Files Allowed To Change
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

