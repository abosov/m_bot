## Files Allowed To Change
- automation/run_codex_task.sh
- tests/test_run_codex_task.py

## Files Not Allowed To Change
- automation/scripts/run_story.sh
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

