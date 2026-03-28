## Files Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- tests/test_run_codex_task.py
- tests/test_run_story.py

## Files Not Allowed To Change
- automation/scripts/finalize_story.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- automation/bundle_packs/*
- automation/bundles/active/*

## Scope Notes
- Только generator-side (run_codex_task.sh)
- Никаких изменений review pipeline
- Только prompt-level enforcement

---

