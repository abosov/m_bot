# Story Bundle Pack

Story-ID: US-AUTO-70
Version: 1

=== FILE: 00_story.md ===

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

=== FILE: 01_context_bundle.md ===

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

=== FILE: 02_file_scope.md ===

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

=== FILE: 03_master_prompt.md ===

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

=== FILE: 04_review_checklist.md ===

## Scope Validation

* APPROVE only if all changed files are inside the allowed scope.
* REJECT if any change introduces new filtering categories or unrelated UX/orchestration behavior.
* REJECT if classification/gate policy semantics are modified.
* REJECT if tests are changed only to relax existing external contracts.
* REJECT if raw companion-inclusive evidence is still used as an authoritative rerun or review baseline for companion-filtered stories.

## Functional Validation

* APPROVE only if rerun-preflight uses the filtered delivery surface as its comparison baseline.
* APPROVE only if review-boundary artifacts are consistent with the same filtered delivery surface.
* REJECT if false non-converging rerun can still occur from filtered-out companion artifacts.
* REJECT if manual-finish continuation semantics regress.
* REJECT if committed-HEAD review semantics regress.
* REJECT if the pipeline silently falls back to raw artifacts when filtered recomputation is missing or inconsistent.

## Verification

* Confirm targeted tests cover run, analyze, and review-boundary recomputation where touched.
* Confirm deterministic failure behavior exists for missing or inconsistent filtered-baseline evidence.
* Confirm the final result is binary: APPROVE only when filtered-baseline recomputation is consistent end to end; otherwise REJECT.
* HARD BLOCK merge if any touched stage consumes a different baseline than the filtered execution delivery surface.

=== FILE: 05_followups.md ===

## Follow-Up Prompt Queue

* None required if US-AUTO-70 fully closes filtered-baseline recomputation for companion-filtered stories.
* If implementation reveals a broader multi-layer contract break outside the bounded filtered-baseline contract, record it in the registry as a contract-level observation rather than creating another automatic micro-split.

## Iteration Notes

* STOP-SPLITTING guard reviewed and not triggered for bundle creation.
* This story is the intended continuation after US-AUTO-72 and should absorb the remaining bounded rerun/review recomputation gap.
* Do not create another follow-up merely for wiring filtered artifacts across the same rerun/review layer; that work belongs in this story.

=== FILE: 06_manual_actions.md ===

## Required Human Actions

1. Where to perform: locally
2. Ensure the repository is clean and synchronized before materializing:
   `git status --short`
3. Save this bundle pack to:
   `automation/bundle_packs/US-AUTO-70.bundle.md`
4. Materialize the bundle:
   `automation/scripts/materialize_story_bundle.sh US-AUTO-70`
5. Validate the bundle:
   `automation/scripts/validate_story_bundle.sh US-AUTO-70`
6. Update the registry entry for US-AUTO-70 and related notes if the workflow expects a separate bundle-artifact commit.
7. If the existing branch `feat/us-auto-70-rerun-preflight-recompute` is the intended working branch, switch to it:
   `git checkout feat/us-auto-70-rerun-preflight-recompute`
8. If that branch is stale or incorrect, delete or rename it explicitly before recreating; do not continue ambiguously.
9. Commit bundle artifacts using the normal handoff workflow.
10. Run the story:
    `automation/scripts/run_story.sh US-AUTO-70`
11. After the run completes, first analyze the latest run and inspect workspace state before any review-stage command:
    `AUTOMATION_RUN_DIR=<latest-run-dir> automation/scripts/analyze_story_run.sh US-AUTO-70 && git status --short`
12. Follow the committed-HEAD/manual-finish workflow strictly. After any new commit, rerun the story and use the fresh latest run directory rather than reusing an older pinned run.
13. Proceed through review stages only after stage-gate invariants are satisfied.
14. Merge only after approve gate on the fresh committed-head run, then clean up branch and return to main.

## Completion Status

* Bundle prepared for materialize + validate.
* Story selected: US-AUTO-70.
* Story intent: stable filtered-baseline recomputation for rerun/review.
* Next operator step after saving bundle: materialize, validate, then switch to the existing intended feature branch if appropriate.
