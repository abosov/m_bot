## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-54.bundle.md`
- `automation/bundles/active/US-AUTO-54/00_story.md`
- `automation/bundles/active/US-AUTO-54/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-54/02_file_scope.md`
- `automation/bundles/active/US-AUTO-54/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-54/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-54/05_followups.md`
- `automation/bundles/active/US-AUTO-54/06_manual_actions.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_run_codex_task.py`
- any file outside the explicit allowlist above

## Scope Notes
Allowed change types:
- minimal logic correction in `review_gate_story_run.sh` for the exact committed-head rerun diff fidelity defect
- focused regression additions or updates in `tests/test_review_gate_story_run.py`
- registry status update for `US-AUTO-54`
- story artifact materialization for this story

Disallowed change types:
- orchestration redesign
- retry loops, continuation logic changes, or operator UX enhancements
- broad refactors across review pipeline scripts
- changing tests to redefine stable external contracts
- widening the story to include unrelated review or runtime defects

If the defect cannot be fixed within this allowlist without violating atomicity, stop and record a follow-up instead of expanding scope.

