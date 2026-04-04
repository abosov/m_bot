
## Files Allowed To Change

automation/scripts/run_story.sh
automation/run_codex_task.sh
tests/test_run_story.py
tests/test_run_codex_task.py

## Files Not Allowed To Change

automation/scripts/analyze_story_run.sh
automation/scripts/classify_review_story_run.sh
automation/scripts/review_gate_story_run.sh
tests/test_analyze_story_run.py
tests/test_classify_review_story_run.py
tests/test_review_gate_story_run.py
tests/test_review_pipeline_validation_contract.py

automation/bundle_packs/US-AUTO-70.bundle.md
automation/bundle_packs/US-AUTO-71.bundle.md

## Scope Notes

Scope filtering must happen **inside pipeline**, not via Codex discipline.

---

