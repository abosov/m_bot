# File Scope — US-AUTO-48

## Files Allowed To Change
Only these files may be changed:

- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-48.bundle.md`
- `automation/bundles/active/US-AUTO-48/00_story.md`
- `automation/bundles/active/US-AUTO-48/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-48/02_file_scope.md`
- `automation/bundles/active/US-AUTO-48/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-48/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-48/05_followups.md`
- `automation/bundles/active/US-AUTO-48/06_manual_actions.md`

## Files Not Allowed To Change
These files are out of scope:

- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`
- `automation/story_change_ledger.jsonl`
- any active bundle or bundle pack outside `US-AUTO-48`
- any docs outside the epic registry unless strictly required for this exact contract

