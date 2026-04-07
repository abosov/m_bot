
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

## Critical Implementation Constraint

For downstream consumers (`ai_review_story_run.sh`, `classify_review_story_run.sh`, `analyze_story_run.sh`, `review_story_run.sh`, `review_gate_story_run.sh`):

- DO NOT delete `recompute_filtered_changed_files_for_run_to`
- DO NOT delete `recompute_filtered_diff_patch_for_run_to`
- DO NOT delete `review_artifact_fidelity_status`
- DO NOT replace `run_filtered_review_artifacts_match_recomputed_surface()` with an existence-only or status-only semantic projection check
- DO NOT broaden the story into a full semantic-projection-only rewrite of downstream consumers

Required behavior:

- `semantic_projection.json` is a preferred validation fast-path when present and valid
- existing recompute/manual-finish/stale-surface logic must remain available as fallback
- manual-finish continuation proof and stale review surface detection must preserve current test contracts
- projection integration must be additive and compatibility-preserving, not a rewrite of downstream fidelity semantics

In other words:
- add projection-aware validation
- preserve legacy recompute-based proof paths
- preserve stale surface rejection behavior
- preserve manual-finish continuation behavior

## Implementation Instructions

1. Generate projection artifact during run stage
2. Persist it into run directory
3. Update downstream stages so they consume and validate projection artifacts when those artifacts are present
4. Preserve compatibility for pinned runs and tests that only contain legacy artifacts such as changed_files.txt and diff.patch
5. Remove all recomputation paths
6. Do not make projection artifact presence a universal hard requirement for every historical or minimal pinned-run fixture
7. Do not remove or weaken downstream recompute-based fidelity helpers that are still used by manual-finish and stale-surface contracts
8. Projection integration must be minimal, additive, and test-contract-preserving
9. If a downstream file is already locally correct, do not refactor it further

## Output

* Projection artifact produced at run stage
* Downstream strictly consumes artifact
* Deterministic behavior across stages

---

