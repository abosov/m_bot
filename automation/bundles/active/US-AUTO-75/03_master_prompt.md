
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

