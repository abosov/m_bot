# US-PAY-2 Review Checklist

## Scope Compliance
- Changes stay within allowed file list from `02_file_scope.md`.
- No forbidden files/areas were modified.
- No hidden scope expansion into API routes/UI/migrations.

## Architecture Compliance
- Implementation aligns with `billing_payments`-centric target path.
- Legacy `BillingPurchase` / `SpecialistProfile.tariff_*` flow is not used as new source of truth.
- Route-layer work remains deferred to `US-PAY-3` and `US-PAY-4`.

## Behavior Validation
- Create-payment request mapping to YooKassa is correct.
- Idempotence key policy is deterministic and retry-safe.
- Provider errors are mapped to controlled internal outcomes.
- Secrets remain backend-only.

## QA Evidence
- `pytest tests/test_billing_subscriptions.py` executed and reported.
- `pytest tests/test_billing_subscription_flow.py` executed and reported.
- New/updated tests cover happy path and failure/idempotence paths.

## Review Classification
Classify findings using:
- `MERGE BLOCKER`
- `MINOR IMPROVEMENT`
- `FOLLOW-UP STORY`

Reference:
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`
