
## Files Allowed To Change

* docs/90_codex/epics/US-AUTO_REGISTRY.md
* automation/run_codex_task.sh
* automation/scripts/run_story.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/review_story_run.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* tests/test_run_codex_task.py
* tests/test_run_story.py
* tests/test_analyze_story_run.py
* tests/test_review_story_run.py
* tests/test_ai_review_story_run.py
* tests/test_review_gate_story_run.py

## Files Not Allowed To Change

* automation/scripts/materialize_story_bundle.sh
* automation/scripts/validate_story_bundle.sh
* automation/scripts/commit_story_artifacts.sh
* automation/story_change_ledger.jsonl
* Any bundle pack other than the materialized/active US-AUTO-70 artifacts created by workflow
* Application code unrelated to automation pipeline review/rerun behavior
* Any CI workflow files unless a direct test fixture demands it, which is not expected here

## Scope Notes

* Allowed change type: recompute filtered review baseline consistently across run/analyze/review consumers.
* Allowed change type: deterministic diagnostics or artifact generation required to support filtered recomputation.
* Allowed change type: tests that verify preserved external contracts under the new filtered-baseline behavior.
* Forbidden: introducing new filtering categories, changing AI review schema, or changing review gate policy semantics.
* Forbidden: modifying tests to accept weaker or broader behavior than current contracts.
* Forbidden: expanding into unrelated operator UX or registry-wide refactors.

