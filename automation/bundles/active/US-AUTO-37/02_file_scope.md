# US-AUTO-37: File Scope

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_run_story.py`
- `tests/test_finalize_story.py`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-37.bundle.md`
- `automation/bundles/active/US-AUTO-37/**`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated CI workflows
- unrelated application code
- broad repository-wide ignore configuration unrelated to this story

