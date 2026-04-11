
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

