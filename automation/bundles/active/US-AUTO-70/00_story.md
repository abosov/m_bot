
## Story ID and Title

US-AUTO-70 — Rerun Preflight Stable Review Recomposition for Companion-Filtered Stories

## Objective

Stabilize the run/analyze/manual-finish continuation path for companion-filtered stories by making rerun-preflight and review baseline recomputation use the same filtered delivery surface that runtime execution already treats as authoritative.

## Scope

This story is limited to the run/manual-finish/review-boundary layer for companion-filtered stories. It must make rerun-preflight decisions and downstream review baseline artifacts recompute from the filtered delivery surface rather than from raw execution-side artifacts.

## Non-goals

* Do not introduce new companion filtering rules.
* Do not change AI review output contracts.
* Do not change review classification or gate policy semantics.
* Do not broaden scope into unrelated pipeline UX improvements.
* Do not alter bundle validation contracts.
* Do not modify tests to weaken existing external behavior contracts.

## Dependencies

* US-AUTO-69 observation chain identifying split between execution filtering and rerun/review recomputation.
* US-AUTO-72 implemented explicit companion isolation for execution delivery surface.
* Existing committed-HEAD review and manual-finish continuation invariants must remain intact.

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

US-AUTO-72 established execution-time companion filtering and fail-closed protection for empty delivery surface. However, rerun-preflight and review baseline inputs can still be derived from raw or pre-filter execution evidence, which can cause false non-converging rerun decisions and unnecessary manual-finish cycles even when the filtered delivery surface is stable.

## Target Outcome

For companion-filtered stories, rerun-preflight, changed_files/diff artifacts, and review-boundary inputs all converge on the same filtered delivery surface. If filtering removes non-delivery companion artifacts, rerun and review logic must treat the filtered result as the authoritative baseline. The pipeline must fail closed when recomputation cannot prove a stable filtered review surface.

## Atomic Task Isolation Contract

This story is atomic. It changes one pipeline responsibility: stable recomputation of rerun/review baseline for companion-filtered stories. It may touch multiple scripts only where strictly required to preserve one contract across run, analyze, review, and gate consumption. It must not introduce new filtering categories or unrelated orchestration behavior.

## Risks

* Medium risk of regression in review-boundary evidence if recomputation sources diverge.
* Medium risk of scope drift into broader delivery filtering policy.
* Medium risk of stale-run handling regressions if new filtered artifacts are not wired consistently.
* High importance of preserving committed-HEAD and manual-finish invariants.

## Manual Actions

* Materialize and validate the bundle before any implementation work.
* Update the registry to mark US-AUTO-70 In Progress and US-AUTO-72 Implemented if not already reflected.
* Implement on a feature branch, not on main.
* Run targeted tests for all touched pipeline stages.
* Run full story workflow after bundle artifact handoff.
* Merge only after approve gate on a fresh committed-head run.

## Acceptance Notes

* Pipeline layer: run / analyze / manual-finish / review-boundary recomputation.
* Story type: atomic, not contract-level escalation.
* Rerun-preflight must use the same filtered delivery surface as execution output.
* Review baseline artifacts must be recomputed from the filtered surface, not raw companion-inclusive evidence.
* False non-converging rerun caused solely by filtered-out companion artifacts must no longer occur.
* If filtered recomputation cannot produce a trustworthy baseline, the pipeline must fail closed with deterministic evidence.
* Existing committed-HEAD review, manual-finish continuation, and gate semantics must remain unchanged.
* External contracts and tests must be satisfied by implementation changes, not by weakening test expectations.

