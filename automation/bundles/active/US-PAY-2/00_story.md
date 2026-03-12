# US-PAY-2: YooKassa Client and Payment Creation Service

## Story ID and Title
- Story ID: `US-PAY-2`
- Title: `YooKassa client and payment creation service`

## Objective
Add backend provider adapter and payment intent service for YooKassa payment creation.

## Scope
- Provider adapter for create-payment request/response handling.
- Payment intent service orchestration around `billing_payments`.
- Idempotence key policy and provider error mapping.
- Service-layer tests for payment creation behavior.

## Non-goals
- No public API endpoint in this story.
- No frontend/UI wiring in this story.
- No webhook runtime processing changes in this story.

## Dependencies
- `US-PAY-1` billing domain model is required baseline.

## Acceptance Notes
- Backend-only secret usage is preserved.
- Retry behavior is safe with idempotence key policy.
- Runtime path aligns with billing domain source of truth (`billing_payments` + related billing domain tables).
