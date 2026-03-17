# US-AUTO-19: File Scope

## Files Allowed To Change
- `automation/scripts/analyze_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-19.bundle.md`
- `automation/bundles/active/US-AUTO-19/**`
- `tests/test_analyze_story_run.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `frontend/**`
- `migrations/**`
- `.github/**`

## Scope Notes
- Add a new read-only script rather than modifying core execution flow
- Do not redesign artifact formats in this story
- Tests should use synthetic run directories and fixture artifacts

