
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
* Fail if recomputation detected
* Fail if projection artifact is present but invalid, stale, or inconsistent with pinned run artifacts
* MUST preserve compatibility for older/minimal pinned-run fixtures that do not contain projection artifacts yet

## Hard Stop Rules

* MUST NOT recompute projection
* MUST NOT call filtering logic in downstream stages
* MUST NOT rebuild projection from inputs
* MUST NOT introduce stage-specific behavior

* MUST NOT source or require automation/scripts/lib/semantic_companion_filter.sh in downstream scripts
* MUST NOT introduce SEMANTIC_COMPANION_FILTER_LIB or any equivalent helper variable in downstream scripts
* MUST NOT add any external helper dependency for semantic filtering in downstream stages

* If semantic projection artifacts exist in the pinned run:
  - downstream scripts MUST validate and consume them
  - invalid or inconsistent projection artifacts MUST fail closed

* If semantic projection artifacts do not exist in the pinned run:
  - downstream scripts MUST NOT fail solely because those projection artifacts are absent
  - downstream scripts MUST fall back to the existing pinned run artifacts already used by the pre-US-AUTO-75 contract
  - backward compatibility for minimal test fixtures and legacy pinned-run artifacts MUST be preserved

## Implementation Instructions

1. Generate projection artifact during run stage
2. Persist it into run directory
3. Update downstream stages so they consume and validate projection artifacts when those artifacts are present
4. Preserve compatibility for pinned runs and tests that only contain legacy artifacts such as changed_files.txt and diff.patch
5. Remove all recomputation paths
6. Do not make projection artifact presence a universal hard requirement for every historical or minimal pinned-run fixture

## Output

* Projection artifact produced at run stage
* Downstream strictly consumes artifact
* Deterministic behavior across stages

---

