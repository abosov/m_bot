# US-PAY-3 Review Checklist

## Architecture Fit
- Authenticated specialist-facing API path is used or extended instead of creating an unnecessary parallel route tree.
- Router stays thin; billing orchestration remains in service layer.
- US-PAY-2 payment creation service is reused instead of duplicating YooKassa provider logic.
- Billing-domain architecture remains the source of truth for payment start flow.

## Scope Control
- Changes stay inside the file scope defined for US-PAY-3.
- No webhook processing logic is added.
- No subscription activation logic is added.
- No access gating changes are introduced.
- No unrelated frontend, calendar, booking, media, or infra changes are introduced.

## Billing Safety
- Route response does not mark subscription as active/succeeded.
- `return_url` is not treated as payment confirmation.
- Duplicate click / retry behavior is guarded by reuse or equivalent idempotent handling for same subscription context.
- No uncontrolled creation of parallel active payment attempts.
- Sensitive provider credentials remain backend-only.

## API Contract
- Request model validates required payment-start input.
- Response model clearly exposes pending/redirect semantics.
- `confirmation_url` is returned on successful payment-start flow.
- Invalid tariff/plan or unavailable purchase conditions are handled explicitly.

## Tests
- Focused pytest coverage exists for route and/or service behavior.
- Success case is covered.
- Invalid tariff/plan case is covered.
- Route auth behavior is covered if repository pattern supports it.
- Duplicate/retry guard or reuse behavior is covered.
- No test failures remain in changed scope.

## Docs
- Docs are updated if implementation changed runtime/API behavior.
- No docs contradict `billing_yookassa_subscription_mvp.md`.
- Legacy flow notes are not accidentally presented as the new source of truth.

## Review Classification Reminder
Classify findings using:
- `MERGE BLOCKER`
- `MINOR IMPROVEMENT`
- `FOLLOW-UP STORY`

Tie-break rule:
- If uncertain between blocker and minor, classify as blocker until risk is resolved.
