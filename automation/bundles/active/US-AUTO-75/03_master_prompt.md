
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

