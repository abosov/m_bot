
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

