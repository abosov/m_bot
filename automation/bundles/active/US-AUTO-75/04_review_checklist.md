
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

