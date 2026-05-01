
## Files Allowed To Change

* automation/run_codex_task.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* automation/scripts/review_story_run.sh
* tests/test_review_gate_story_run.py
* tests/test_ai_review_story_run.py
* tests/test_analyze_story_run.py
* tests/test_classify_review_story_run.py
* tests/test_review_story_run.py

## Files Not Allowed To Change

* docs/**
* automation/bundles/**
* automation/bundle_packs/**
* unrelated scripts
* unrelated tests

## Expected New Files

* pinned run artifact: `semantic_projection.json`

## Scope Notes

* Producer changes must be narrowly limited to projection emission and preservation of separate review vs delivery surfaces
* Downstream changes must be additive and compatibility-preserving
* `automation/scripts/lib/semantic_companion_filter.sh` is out of scope unless a failing test proves it is the minimal root cause
* Do not broaden producer changes into generic scope/rollback behavior rewrites

---

