
## Scope Validation

* Only allowed files modified

## Functional Validation

* When projection artifact is present, downstream validates and uses it
* When projection artifact is absent, downstream preserves legacy pinned-run behavior without recomputation
* No recomputation

## Verification

* committed-head rerun converges
* no fidelity drift

## Hard Block Conditions

* Present-but-invalid projection artifact → REJECT
* Recomputation → REJECT
* Scope violation → REJECT
* HEAD drift → REJECT

## Regression Validation

* All tests pass

## Final Decision

* APPROVE or REJECT

---

