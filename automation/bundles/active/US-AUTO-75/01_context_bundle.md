
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

