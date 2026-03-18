# US-AUTO-22: File Scope

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-22.bundle.md`
- `automation/bundles/active/US-AUTO-22/**`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Not Allowed To Change
- `automation/scripts/**`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/**`
- `backend/**`

## Scope Notes
- This story updates Codex workflow documentation, prompt templates, the story bundle pack, and the materialized active bundle for US-AUTO-22.
- Do not change runtime automation, enforcement scripts, or tests in this story.
- If script enforcement is needed, create a separate follow-up story.