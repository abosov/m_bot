# US-AUTO-46: File Scope

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_review_story_run.py`
- `tests/test_analyze_story_run.py`
- `automation/bundle_packs/US-AUTO-46.bundle.md`
- `automation/bundles/active/US-AUTO-46/**`
- `tests/test_review_gate_story_run.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Scope Notes
- Prefer the narrowest possible implementation in `review_story_run.sh`.
- Touch downstream scripts only if needed to keep the review-boundary contract coherent and testable.
- Do not introduce auto-commit or implicit workspace mutation.
- Do not expand into bundle sync or unrelated workflow simplification.

