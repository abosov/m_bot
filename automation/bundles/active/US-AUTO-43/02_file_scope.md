# US-AUTO-43: File Scope

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_review_pipeline_validation_contract.py`
- `tests/test_analyze_story_run.py`
- `tests/test_review_gate_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-43.bundle.md`
- `automation/bundles/active/US-AUTO-43/**`

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/run_codex_task.sh
- automation/scripts/validate_story_bundle.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/story_change_ledger.sh
- backend/**
- frontend/**
- database/**

## Scope Notes
- only validation and failure handling changes allowed
- classification/gate logic must not change
- minimal patch only

