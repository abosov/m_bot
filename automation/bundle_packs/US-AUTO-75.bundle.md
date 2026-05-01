Story Bundle Pack
Story-ID: US-AUTO-75
Version: 2

=== FILE: 00_story.md ===

## Story ID and Title

US-AUTO-75 — Additive review-fidelity projection contract for semantic companion filtering

## Objective

Introduce a producer-owned `semantic_projection.json` artifact and integrate it into downstream review-fidelity validation as a preferred fast-path, while preserving existing recompute-based fallback behavior, manual-finish continuation proof, stale review surface detection, committed-HEAD review contracts, rollback behavior, and scope-validation behavior.

## Background

US-AUTO-74 established centralized semantic companion filtering semantics, but downstream review consumers still relied on recomputation-heavy fidelity checks. That made the pipeline vulnerable to drift between producer and consumers.

However, the required fix is narrower than a rewrite:
the pipeline must not be converted into a projection-only model.
Instead, projection must be integrated as an additive validation layer.

## Scope

* Producer-side projection artifact emission in `automation/run_codex_task.sh`
* Additive projection-aware validation in downstream review consumers
* Preservation of existing recompute/manual-finish/stale-surface fallback contracts
* Preservation of existing producer-side scope guard, out-of-scope rejection, rollback, and signal-handling contracts

Pipeline layer: run + analyze + review + classify + gate

Type: contract-level, compatibility-preserving

## Non-goals

* Do not rewrite downstream consumers into projection-only mode
* Do not remove existing recompute-based proof paths
* Do not weaken stale review surface detection
* Do not weaken manual-finish continuation validation
* Do not broaden semantic filtering semantics
* Do not refactor unrelated producer logic
* Do not change unrelated operator UX or review classification behavior

## Dependencies

* US-AUTO-74

## Source of Truth

* Producer-emitted pinned run artifacts:
  * `changed_files.txt`
  * `diff.patch`
  * `review_changed_files.txt`
  * `semantic_projection.json`
* Existing committed-HEAD/manual-finish review contracts already enforced by tests

## Current Code Reality

* Producer can compute delivery and review surfaces
* Downstream review consumers have established recompute/manual-finish fidelity behavior
* Broad rewrite attempts cause regressions in:
  * stale review surface detection
  * manual-finish continuation
  * producer scope/rollback contracts
  * review gate fidelity behavior

## Target Outcome

* Producer emits `semantic_projection.json`
* Downstream consumers may validate and trust that artifact when present and valid
* Legacy/minimal pinned runs without projection remain supported
* Existing recompute/manual-finish/stale-surface behavior remains intact as fallback
* Producer scope validation, rollback, and signal-handling behavior remain unchanged except where strictly needed for projection emission

## Acceptance Criteria

* `automation/run_codex_task.sh` emits `semantic_projection.json`
* Projection artifact records sha256 for:
  * `changed_files.txt`
  * `diff.patch`
  * `review_changed_files.txt`
* Downstream consumers prefer projection validation when present and valid
* Legacy pinned runs without projection still work
* Existing stale review surface rejection tests still pass
* Existing manual-finish continuation tests still pass
* Existing review gate fidelity tests still pass
* Existing producer scope-guard / rollback / signal-handling tests still pass
* Full `run_story.sh US-AUTO-75` reaches success boundary
* Committed-head review chain completes without fidelity regressions

## Acceptance Notes

* This story is additive, not a rewrite
* Projection is a preferred fast-path, not a universal replacement for downstream fidelity logic
* Existing contracts must be preserved unless an explicit failing test proves that a narrower change is impossible

---

=== FILE: 01_context_bundle.md ===

## Source of Truth

* `automation/run_codex_task.sh`
* Existing downstream review contracts in:
  * `automation/scripts/ai_review_story_run.sh`
  * `automation/scripts/analyze_story_run.sh`
  * `automation/scripts/classify_review_story_run.sh`
  * `automation/scripts/review_gate_story_run.sh`
  * `automation/scripts/review_story_run.sh`
* Pinned run artifacts:
  * `changed_files.txt`
  * `diff.patch`
  * `review_changed_files.txt`
  * `semantic_projection.json`

## Current Code Reality

* Producer and consumers already have meaningful fidelity/recompute/manual-finish logic
* Codex tends to over-simplify this class of task into a projection-only rewrite
* That broad rewrite breaks existing contracts and cascades into many tests

## Architectural Intent

Shift from:

recompute-only downstream fidelity validation

to:

projection-aware preferred validation with legacy fallback preserved

This is not:
projection-only downstream rewrite

## Risks

* Deleting recompute helpers that are still required by fallback/manual-finish paths
* Replacing stale-surface logic with mere projection-presence checks
* Broad producer rewrites that break scope guard / rollback / signal handling
* Modifying `semantic_companion_filter.sh` without a minimal failing-test justification
* Treating missing projection as universal failure for legacy/minimal pinned-run fixtures

## Acceptance Notes

Projection must be:

* producer-owned
* persisted into pinned run artifacts
* validated against pinned run artifacts
* preferred when present and valid
* optional for backward compatibility when absent from legacy/minimal pinned runs

---

=== FILE: 02_file_scope.md ===

## Files Allowed To Change

* automation/run_codex_task.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* automation/scripts/review_story_run.sh
* tests/test_run_codex_task.py
* tests/test_review_gate_story_run.py
* tests/test_ai_review_story_run.py
* tests/test_analyze_story_run.py
* tests/test_classify_review_story_run.py
* tests/test_review_story_run.py

## Files Not Allowed To Change

* docs/**
* automation/bundles/**
* automation/bundle_packs/**
* automation/bundles/active/US-AUTO-75/**
* docs/90_codex/epics/US-AUTO_REGISTRY.md
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

=== FILE: 03_master_prompt.md ===

## Role

You are implementing a contract-level, compatibility-preserving fix for review-fidelity projection in the Codex pipeline.

## Goal

Emit a producer-owned `semantic_projection.json` artifact during run stage and integrate it into downstream review-fidelity validation as a preferred fast-path, without rewriting downstream consumers or weakening existing recompute/manual-finish/stale-surface/rollback/scope contracts.

## Source of Truth

* pinned run artifacts produced by `automation/run_codex_task.sh`
* existing committed-HEAD/manual-finish/stale-surface fidelity behavior already covered by tests

## Files Allowed To Change

* automation/run_codex_task.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* automation/scripts/review_story_run.sh

## Files Not Allowed To Change

* docs/**
* bundle files
* unrelated scripts
* unrelated tests
* `automation/scripts/lib/semantic_companion_filter.sh` unless a failing test proves that library itself is the minimal root cause

## Execution Gate

* Fail if workspace dirty
* Fail if not HEAD aligned
* Fail if scope guard would be weakened
* Fail if rollback or signal-handling contracts would be weakened
* Fail if projection artifact is present but invalid, stale, or inconsistent with pinned run artifacts
* Preserve compatibility for older/minimal pinned-run fixtures that do not contain projection artifacts yet

## Hard Stop Rules

* MUST NOT rewrite downstream consumers into projection-only mode
* MUST NOT delete recompute/manual-finish/stale-surface helper paths that are still needed by fallback contracts
* MUST NOT replace fidelity logic with projection existence-only or status-only checks
* MUST NOT broaden changes in `automation/run_codex_task.sh` beyond the exact producer work needed for projection emission and surface preservation
* MUST NOT weaken:
  * out-of-scope docs rejection
  * mixed companion + real out-of-scope rejection
  * no-companion review surface behavior
  * SIGTERM failure handling
  * rollback failure surfacing
  * generic file-scope validation
* MUST NOT source or require `automation/scripts/lib/semantic_companion_filter.sh` in downstream scripts
* MUST NOT introduce new downstream dependency on producer-only helper paths
* MUST NOT make projection artifact presence a universal hard requirement for every historical or minimal pinned-run fixture

## Critical Implementation Constraint

For downstream consumers (`ai_review_story_run.sh`, `classify_review_story_run.sh`, `analyze_story_run.sh`, `review_story_run.sh`, `review_gate_story_run.sh`):

* DO NOT delete:
  * `recompute_filtered_changed_files_for_run_to`
  * `recompute_filtered_diff_patch_for_run_to`
  * `review_artifact_fidelity_status`
  * other existing helper paths that are still used by manual-finish/stale-surface fallback contracts
* DO NOT replace `run_filtered_review_artifacts_match_recomputed_surface()` with an existence-only or status-only semantic projection check
* DO NOT broaden this story into a semantic-projection-only rewrite of downstream consumers

Required downstream behavior:

* If `semantic_projection.json` is present and valid:
  * use it as a preferred validation fast-path
* If `semantic_projection.json` is absent:
  * preserve legacy pinned-run behavior
* If `semantic_projection.json` is invalid:
  * fail closed
* manual-finish continuation proof must continue to work
* stale review surface detection must continue to work
* committed-HEAD review contracts must continue to work

In other words:

* add projection-aware validation
* preserve legacy recompute-based proof paths
* preserve stale surface rejection behavior
* preserve manual-finish continuation behavior
* preserve review gate fidelity behavior

## Producer Constraint

For `automation/run_codex_task.sh`:

Allowed producer changes are limited to:

* emit `semantic_projection.json`
* record sha256 for:
  * `changed_files.txt`
  * `diff.patch`
  * `review_changed_files.txt`
* preserve separate delivery vs review surfaces
* preserve same-story artifact filtering
* preserve non-runtime companion filtering
* preserve existing scope validation contracts
* preserve rollback and signal-handling contracts

Forbidden producer changes:

* do not weaken out-of-scope rejection logic
* do not weaken mixed companion + real out-of-scope rejection logic
* do not weaken no-companion review surface behavior
* do not weaken rollback behavior
* do not weaken SIGTERM behavior
* do not broaden into generic materialization/rollback rewrite

## Implementation Instructions

1. Emit `semantic_projection.json` during run stage
2. Persist it into pinned run artifacts
3. Record enough metadata to validate the projection artifact against:
   * `changed_files.txt`
   * `diff.patch`
   * `review_changed_files.txt`
4. Update downstream consumers so they prefer projection validation when projection is present and valid
5. Preserve compatibility for pinned runs and tests that contain only legacy artifacts such as `changed_files.txt` and `diff.patch`
6. Preserve recompute/manual-finish/stale-surface fallback paths
7. Keep downstream integration minimal, additive, and test-contract-preserving
8. Keep producer integration narrow and guard-contract-preserving
9. If a downstream file is already locally correct, do not refactor it further
10. If a producer or downstream change is not required by a failing test or this story’s exact contract, do not make that change

## Output

* Producer emits `semantic_projection.json`
* Downstream validates and prefers projection when available
* Legacy fallback remains intact
* Deterministic behavior across stages
* Existing producer guard/rollback contracts remain intact

---

=== FILE: 04_review_checklist.md ===

## Scope Validation

* Only allowed files modified
* `semantic_companion_filter.sh` unchanged unless a minimal failing-test justification exists

## Functional Validation

* Producer emits `semantic_projection.json`
* Projection hashes match pinned run artifacts
* When projection is present and valid, downstream uses it as a preferred validation fast-path
* When projection is absent, downstream preserves legacy pinned-run behavior
* Existing recompute/manual-finish/stale-surface behavior remains intact
* Existing producer scope/rollback/signal-handling behavior remains intact

## Verification

* committed-head rerun converges
* no fidelity drift
* no rollback/scope regression
* no stale-surface/manual-finish regression

## Hard Block Conditions

* Invalid projection artifact → REJECT
* Recomputation-only rewrite of downstream → REJECT
* Producer guard/rollback regression → REJECT
* Scope violation → REJECT
* HEAD drift → REJECT

## Regression Validation

* All targeted tests pass
* Full `run_story.sh US-AUTO-75` reaches success boundary

## Final Decision

* APPROVE or REJECT

---

=== FILE: 05_followups.md ===

## Follow-Up Prompt Queue

* Consider a future governance story to codify “contract-sensitive downstream stories must be additive, not rewrite-oriented”

## Iteration Notes

* US-AUTO-75 must remain additive and compatibility-preserving
* Projection integration must not become a broad downstream rewrite
* STOP-SPLITTING boundary reached

---

=== FILE: 06_manual_actions.md ===

## Required Human Actions

* automation/scripts/commit_story_artifacts.sh US-AUTO-75
* automation/scripts/run_story.sh US-AUTO-75
* automation/scripts/analyze_story_run.sh US-AUTO-75

## Completion Status

* Always use latest run
* Do not reuse old run
* Review only after committed-head rerun
* Gate only on pinned artifacts
* If successful materialization leaves a dirty workspace, commit the materialized implementation changes before running review-stage commands