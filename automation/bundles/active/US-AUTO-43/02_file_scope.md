# US-AUTO-43: File Scope

## Files Allowed To Change
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_*
- tests/test_review_pipeline_*

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

