# US-AUTO-17: File Scope

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-17.bundle.md`
- `automation/bundles/active/US-AUTO-17/**`

## Files Not Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- Keep this story strictly about Repository Map Injection v2.
- Do not introduce new pipeline stages.
- Do not alter allowed-files guard behavior.
- Do not add console UX, chaining, or blocker/warn semantics here.
- Reuse existing curated docs and bundle scope instead of inventing a new metadata system.

