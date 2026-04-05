
## Scope Validation

Reject if ANY forbidden file changed.

## Functional Validation

Approve only if:

* explicit companion isolation is implemented
* contaminated diff no longer blocks delivery only in the explicit companion case
* real out-of-scope changes still block before pytest
* success boundary is reachable without weakening fail-closed scope enforcement

## Verification

Tests must:

* simulate explicit companion contamination
* simulate real out-of-scope violations
* assert delivery succeeds only for the explicit companion case
* assert real scope violations still fail

---

