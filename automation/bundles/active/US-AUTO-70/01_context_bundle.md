
## Source of Truth

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

## Current Code Reality

Execution companion filtering now exists and protects the delivery surface from non-delivery companion artifacts. The remaining gap is that rerun-preflight and review-baseline recomputation may still rely on raw execution evidence or pre-filter artifact sets. That mismatch can surface as review_changed_files divergence, false non-converging rerun, or unnecessary manual-finish even when the actual filtered delivery surface is stable.

## Architectural Intent

There must be exactly one authoritative review surface for a story run. Once companion filtering defines the delivery surface, all downstream rerun and review-boundary decisions must derive from that same filtered surface. The system must stay deterministic, committed-HEAD based, and fail closed when it cannot prove equivalence.

## Risks

* Hidden coupling between run_codex_task output artifacts and downstream recomputation.
* Drift between filtered changed_files.txt, diff.patch, and review consumption.
* Accidental broadening into classification/gate policy changes.
* Regressions in stale-run or manual-finish diagnostics if recomputation paths are only partially updated.

## Acceptance Notes

* The filtered delivery surface is the only valid baseline for companion-filtered stories.
* Raw companion-inclusive evidence must not trigger a rerun/manual-finish mismatch when filtered output is stable.
* Review consumers must read artifacts that reflect the filtered baseline.
* Deterministic failure messaging must remain available if recomputation fails or artifacts are inconsistent.
* No STOP-SPLITTING escalation is required here because the unresolved gap is one bounded contract: filtered-baseline recomputation.

