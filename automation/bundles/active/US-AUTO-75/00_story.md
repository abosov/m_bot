
## Story ID and Title

US-AUTO-75 — Enforce run-artifact-based review-fidelity projection contract for semantic companion filtering

## Objective

Define and enforce a strict contract where semantic filtering projection is produced once during run stage and consumed as a persisted artifact by all downstream stages, eliminating recomputation drift and ensuring deterministic review fidelity.

## Background

US-AUTO-74 centralized semantic companion filtering logic. However, pipeline still fails with `blocked_review_artifact_fidelity` due to implicit recomputation of projection in downstream stages.

Root cause:
projection is treated as logic, not as a persisted artifact.

## Scope

* Introduce run-stage projection artifact
* Enforce downstream consumption of this artifact
* Remove all recomputation paths
* Update run-stage producer logic where needed so projection is persisted into run artifacts and becomes the only downstream source for review-fidelity consumption

Pipeline layer: run + analyze + review + classify + gate (contract-level)

Type: contract-level

Fail-closed behavior:

* Missing projection artifact → BLOCK
* Recomputed projection → BLOCK
* Mismatch between stages → BLOCK

## Non-goals

* Do not change classification logic
* Do not modify manual-finish
* Do not change operator UX
* Do not expand filtering semantics

## Dependencies

* US-AUTO-74

## Source of Truth

* semantic_companion_filter.sh
* run-stage generated projection artifact

## Current Code Reality

* Helper is centralized
* Projection is recomputed in multiple stages
* Leads to non-converging runs

## Target Outcome

* Projection produced exactly once during run
* All stages consume identical artifact
* No recomputation
* Deterministic convergence

## Acceptance Criteria

* No `blocked_review_artifact_fidelity`
* No recomputation of projection
* Projection artifact exists and is reused
* All tests pass

## Acceptance Notes

* Projection must be treated as immutable run artifact
* Contract must be fail-closed

---

