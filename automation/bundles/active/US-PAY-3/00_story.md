# US-PAY-3: Payment Creation API and Redirect Flow

## Story ID and Title
- Story ID: `US-PAY-3`
- Title: `Payment creation API and redirect flow`

## Objective
Add an authenticated backend API endpoint that starts a YooKassa payment for specialist subscription purchase and returns redirect/confirmation data without treating return_url as payment confirmation.

## Scope
- Authenticated backend endpoint for starting subscription payment.
- Tariff/plan validation for the requested purchase.
- Creation or reuse of payment intent in billing domain flow.
- Response payload with confirmation/redirect URL and pending-payment state.
- Route/service tests for happy path and key guardrails.

## Non-goals
- No webhook processing in this story.
- No subscription activation from UI return flow.
- No billing access gating changes in this story.
- No frontend billing UI implementation in this story beyond API contract if needed.
- No autopay, receipts, refunds, or capture-lifecycle expansion.

## Dependencies
- `US-PAY-1` billing domain model is required baseline.
- `US-PAY-2` YooKassa client and payment creation service is required baseline.

## Acceptance Notes
- `return_url` is informational only and never activates access.
- Payment creation must be idempotent/retry-safe.
- Pending state remains until webhook-based confirmation in later story.
- Implementation must not allow accidental double-start of equivalent active payment flow for the same subscription context.
