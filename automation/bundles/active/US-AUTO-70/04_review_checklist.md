
## Scope Validation

* APPROVE only if all changed files are inside the allowed scope.
* REJECT if any change introduces new filtering categories or unrelated UX/orchestration behavior.
* REJECT if classification/gate policy semantics are modified.
* REJECT if tests are changed only to relax existing external contracts.
* REJECT if raw companion-inclusive evidence is still used as an authoritative rerun or review baseline for companion-filtered stories.

## Functional Validation

* APPROVE only if rerun-preflight uses the filtered delivery surface as its comparison baseline.
* APPROVE only if review-boundary artifacts are consistent with the same filtered delivery surface.
* REJECT if false non-converging rerun can still occur from filtered-out companion artifacts.
* REJECT if manual-finish continuation semantics regress.
* REJECT if committed-HEAD review semantics regress.
* REJECT if the pipeline silently falls back to raw artifacts when filtered recomputation is missing or inconsistent.

## Verification

* Confirm targeted tests cover run, analyze, and review-boundary recomputation where touched.
* Confirm deterministic failure behavior exists for missing or inconsistent filtered-baseline evidence.
* Confirm the final result is binary: APPROVE only when filtered-baseline recomputation is consistent end to end; otherwise REJECT.
* HARD BLOCK merge if any touched stage consumes a different baseline than the filtered execution delivery surface.

