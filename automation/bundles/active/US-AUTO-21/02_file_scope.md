# US-AUTO-21: File Scope

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-21.bundle.md`
- `automation/bundles/active/US-AUTO-21/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- This story enforces review/gate safety boundary only.
- Do not redesign run artifact generation.
- Do not add auto-commit or hidden git mutation behavior.
- Prefer fail-fast prechecks in review-stage scripts over deeper runner changes.

