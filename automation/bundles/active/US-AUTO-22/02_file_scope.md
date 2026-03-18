# US-AUTO-22: File Scope

## Files Allowed To Change
- `automation/bundle_packs/US-AUTO-22.bundle.md`
- `automation/bundles/active/US-AUTO-22/00_story.md`
- `automation/bundles/active/US-AUTO-22/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-22/02_file_scope.md`
- `automation/bundles/active/US-AUTO-22/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-22/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-22/05_followups.md`
- `automation/bundles/active/US-AUTO-22/06_manual_actions.md`
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
- This exact allowlist matches the reviewed US-AUTO-22 changed-file set: the bundle pack, all seven materialized active-bundle files, and the five Codex docs/template files updated by the story.
- Do not change runtime automation, enforcement scripts, or tests in this story.
- If script enforcement is needed, create a separate follow-up story.
