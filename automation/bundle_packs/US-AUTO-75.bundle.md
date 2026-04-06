Story Bundle Pack
Story-ID: US-AUTO-75
Version: 1

=== FILE: 00_story.md ===

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

=== FILE: 01_context_bundle.md ===

## Source of Truth

* semantic_companion_filter.sh
* run artifact: semantic_projection.json (or equivalent)

## Current Code Reality

* Projection is implicit
* Stages recompute filtering independently

## Architectural Intent

Shift from:

logic-based projection

to:

artifact-based projection

## Risks

* Hidden recomputation paths
* Tests expecting old behavior
* Partial adoption across stages

## Acceptance Notes

Projection must be:

* produced once
* persisted
* immutable
* consumed, not recomputed

---

=== FILE: 02_file_scope.md ===

## Files Allowed To Change

* automation/run_codex_task.sh
* automation/scripts/lib/semantic_companion_filter.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* automation/scripts/review_story_run.sh

## Files Not Allowed To Change

* docs/**
* automation/bundles/**
* automation/bundle_packs/**
* unrelated scripts

## Expected New Files

* run artifact file (e.g. semantic_projection.json)

## Scope Notes

* MUST introduce persisted projection artifact
* MUST remove recomputation paths

---

=== FILE: 03_master_prompt.md ===

## Role

You are implementing a contract-level fix enforcing artifact-based projection in the Codex pipeline.

## Goal

Ensure projection is produced once at run stage and consumed by all downstream stages without recomputation.

## Source of Truth

* semantic_companion_filter.sh
* projection artifact generated at run stage

## Files Allowed To Change

* automation/run_codex_task.sh
* automation/scripts/lib/semantic_companion_filter.sh
* automation/scripts/ai_review_story_run.sh
* automation/scripts/analyze_story_run.sh
* automation/scripts/classify_review_story_run.sh
* automation/scripts/review_gate_story_run.sh
* automation/scripts/review_story_run.sh

## Files Not Allowed To Change

* docs/**
* bundle files
* unrelated scripts

## Execution Gate

* Fail if workspace dirty
* Fail if not HEAD aligned
* Fail if projection artifact missing
* Fail if recomputation detected

## Hard Stop Rules

* MUST NOT recompute projection
* MUST NOT call filtering logic in downstream stages
* MUST NOT rebuild projection from inputs
* MUST NOT introduce stage-specific behavior

* MUST NOT source or require automation/scripts/lib/semantic_companion_filter.sh in downstream scripts
* MUST NOT introduce SEMANTIC_COMPANION_FILTER_LIB or any equivalent helper variable in downstream scripts
* MUST NOT add any external helper dependency for semantic filtering in downstream stages

* Downstream scripts MUST rely only on:
  - persisted run artifacts
  - existing in-file filtering logic already present in the script

## Implementation Instructions

1. Generate projection artifact during run stage
2. Persist it into run directory
3. Replace all downstream filtering with artifact consumption
4. Remove all recomputation paths

## Output

* Projection artifact produced at run stage
* Downstream strictly consumes artifact
* Deterministic behavior across stages

---

=== FILE: 04_review_checklist.md ===

## Scope Validation

* Only allowed files modified

## Functional Validation

* Projection artifact exists
* Downstream uses artifact only
* No recomputation

## Verification

* committed-head rerun converges
* no fidelity drift

## Hard Block Conditions

* Missing artifact → REJECT
* Recomputation → REJECT
* Scope violation → REJECT
* HEAD drift → REJECT

## Regression Validation

* All tests pass

## Final Decision

* APPROVE or REJECT

---

=== FILE: 05_followups.md ===

## Follow-Up Prompt Queue

* None (contract-level closure)

## Iteration Notes

* Resolves projection contract gap from US-AUTO-74
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