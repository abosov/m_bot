
## Scope Validation

HARD BLOCK if any changed file is outside the allowed scope.

HARD BLOCK if the implementation changes:

* manual-finish semantics
* rerun convergence semantics
* bundle validator/materializer logic
* unrelated operator UX behavior

HARD BLOCK if old story-level code-only gating remains a controlling factor for companion filtering.

## Functional Validation

Review must confirm all of the following:

* a semantic non-runtime companion artifact classifier exists
* filtering is path-semantic, not story-type based
* mixed-scope stories can still receive correct filtering
* docs-only non-runtime artifacts are excluded only where intended
* runtime-critical paths remain included
* all relevant downstream stages use the same contract and do not drift

Reject if any consumer still computes a different filtered surface from the others.

## Verification

Require targeted automated tests covering:

* mixed-scope + non-runtime docs case
* docs-only non-runtime artifact case
* runtime-critical path inclusion case
* cross-stage consistency for filtered changed files / diff.patch / review inputs where applicable

Binary outcome only:

* APPROVE if all scope, functional, and verification checks pass
* REJECT otherwise

