
## Files Allowed To Change

* `automation/run_codex_task.sh`
* `automation/scripts/run_story.sh`
* `automation/scripts/analyze_story_run.sh`
* `automation/scripts/review_story_run.sh`
* `automation/scripts/ai_review_story_run.sh`
* `automation/scripts/classify_review_story_run.sh`
* `automation/scripts/review_gate_story_run.sh`
* `tests/test_run_codex_task.py`
* `tests/test_run_story.py`
* `tests/test_analyze_story_run.py`
* `tests/test_review_story_run.py`
* `tests/test_ai_review_story_run.py`
* `tests/test_classify_review_story_run.py`
* `tests/test_review_gate_story_run.py`
* `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change

* `automation/scripts/materialize_story_bundle.sh`
* `automation/scripts/validate_story_bundle.sh`
* bundle validator contract files unrelated to this story
* unrelated application/runtime product code outside automation pipeline
* GitHub workflow files
* secrets, environment configuration, or deployment scripts
* any active story bundle artifacts other than US-AUTO-73 bundle pack/materialized files created through the normal workflow

## Scope Notes

Allowed change types:

* add or refactor a shared semantic helper for non-runtime companion artifact classification
* replace old heuristic checks with the shared helper
* align tests to the new contract
* update registry story status/notes for this story

Forbidden change types:

* broad refactors unrelated to companion filtering
* operator UX rewrites
* retry/manual-finish semantics changes
* introducing alternate fallback heuristics
* editing materialized active bundle files by hand instead of through the bundle workflow

