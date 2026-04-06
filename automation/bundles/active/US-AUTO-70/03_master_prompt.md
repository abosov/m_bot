
## Role

You are the implementation engineer for US-AUTO-70 working inside the Codex automation pipeline with strict fail-closed governance.

## Goal

Implement stable rerun-preflight and review-baseline recomputation for companion-filtered stories so that all downstream run/analyze/review decisions use the same filtered delivery surface already established by execution filtering.

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
* tests/test_classify_review_story_run.py
* tests/test_review_gate_story_run.py

## Files Not Allowed To Change

* automation/scripts/materialize_story_bundle.sh
* automation/scripts/validate_story_bundle.sh
* automation/scripts/commit_story_artifacts.sh
* automation/story_change_ledger.jsonl
* Any unrelated application or deployment files
* Any bundle artifacts other than those produced by the normal story workflow

## Atomic Task Isolation Contract

This story is atomic and limited to one contract: filtered-baseline recomputation for rerun and review. Do not add new companion filters. Do not change classification or gate decision policy. Do not weaken external test contracts. Do not introduce fallback logic that silently mixes raw and filtered surfaces. If filtered recomputation cannot be proven correct, fail closed with deterministic evidence.

## Execution Gate

Before coding, verify the workspace is on a feature branch and not on main. Treat the filtered delivery surface as authoritative. Any proposed change that expands into unrelated validation, retry UX, or orchestration behavior is out of scope and must be rejected.

## Implementation Requirements

* Ensure rerun-preflight derives its comparison surface from the filtered delivery artifacts, not raw companion-inclusive output.
* Ensure downstream review artifacts such as changed_files.txt and diff.patch are recomputed or consumed in a way that matches the filtered delivery surface.
* Preserve committed-HEAD review semantics and manual-finish continuation invariants.
* Preserve deterministic fail-closed behavior when recomputation inputs are missing, stale, or inconsistent.
* Keep artifact naming and flow compatible with existing run/analyze/review/gate scripts.
* Update registry status for US-AUTO-70 consistently with implementation progress.
* Add or update focused tests for the filtered-baseline recomputation contract across touched stages.
* Fix regressions in implementation, not by weakening tests or changing external behavior contracts.

## Verification Requirements

* Run targeted tests for all touched scripts and artifact contracts.
* Verify that companion-filtered stories no longer produce false non-converging rerun solely because filtered-out companion artifacts were present in raw execution output.
* Verify that review and gate consume filtered-baseline artifacts consistently.
* Verify deterministic failure behavior when filtered recomputation cannot establish a trustworthy baseline.
* Verify no regression in committed-HEAD review enforcement or manual-finish continuation handling.

## Output

Produce only the required code, tests, and registry updates within the allowed file scope. Keep changes minimal, deterministic, and fail closed. Do not add explanatory prose to repository files beyond what the touched files conventionally require.

