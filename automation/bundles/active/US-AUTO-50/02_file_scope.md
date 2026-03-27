## Files Allowed To Change
- automation/scripts/ai_review_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_analyze_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_review_pipeline.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/scripts/finalize_story.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- automation/bundle_packs/*
- automation/bundles/active/*

## Scope Notes
- Только review pipeline
- Никаких изменений execution pipeline
- Только validation + fail-closed

---

