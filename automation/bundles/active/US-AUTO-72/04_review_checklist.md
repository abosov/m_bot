
## Scope Validation

Reject if ANY forbidden file changed.

## Functional Validation

Approve only if:

* subset extraction implemented
* contaminated diff no longer blocks delivery
* success boundary reachable

## Verification

Tests must:

* simulate contaminated diff
* assert only allowed subset applied

---

