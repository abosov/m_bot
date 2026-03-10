# YooKassa Subscription Billing MVP Architecture

## Status
Proposed / MVP target.

## Purpose
Define the MVP architecture for specialist subscription billing via YooKassa so implementation can proceed in atomic user stories without changing product/runtime behavior outside approved scope.

## Scope
- Monthly specialist subscription payments through YooKassa hosted payment flow.
- Manual monthly renewal in MVP (specialist initiates each new cycle).
- Access activation/deactivation decisions based on Zumbot billing domain state.
- Idempotent webhook ingestion and event processing.
- Audit-focused billing logs sufficient for support and reconciliation.

## Non-goals
- Automatic recurring charges (autopay).
- Fiscalization details implementation (receipts / 54-FZ).
- Automated refunds.
- Promo-code discount engine.
- Full accounting/reconciliation console.

## Product Decision: Manual Monthly Renewal First
MVP uses manual monthly renewal only. A specialist pays each period by starting a new payment. No stored-payment-method charging is performed in MVP.

## External Provider Boundary
- YooKassa is the payment provider and external status signal.
- Zumbot database is the source of truth for feature access.
- `return_url` is a UX redirect endpoint only and is **not** a payment success source of truth.
- Access changes happen only after validated billing-domain transitions (typically from webhook-confirmed success).

## High-level Flow
1. Specialist selects a tariff and starts payment from billing UI.
2. Backend creates YooKassa payment with idempotence key and stores local payment record.
3. Specialist is redirected to YooKassa `confirmation_url`.
4. Specialist returns to `return_url` page (status shown as pending/checking until backend confirms).
5. YooKassa webhook is received and validated.
6. Billing domain updates payment and subscription state idempotently.
7. Single domain access decision point reads active subscription state for all paid features.

## Detailed Lifecycle

### 1) Create payment
- Validate specialist eligibility and selected tariff.
- Create `billing_payments` row with `new` status and correlation identifiers.
- Call YooKassa create-payment API using backend secret key only.
- On successful provider create-payment response, transition payment to `pending` and persist provider `payment_id`, confirmation metadata, amount/currency snapshot.
- On explicit provider create-payment failure (definitive non-timeout error response), transition payment to `error` and preserve error context for retry/support investigation.

### 2) Redirect to `confirmation_url`
- Frontend navigates specialist to provider-hosted confirmation page.
- UI must not mark subscription active during redirect stage.

### 3) `return_url` behavior
- On return, UI requests current billing status from backend.
- `return_url` may show "payment processing".
- `return_url` never activates subscription directly.

### 4) Webhook handling
- Verify webhook authenticity/signature strategy per YooKassa contract.
- Persist raw event envelope in `billing_webhook_events` before business processing.
- Process idempotently by unique provider event/payment identifiers.
- Reprocessing same webhook must be a no-op for already-applied transition.

### 5) Subscription activation / renewal
- Successful payment transition (`succeeded`) creates or extends subscription period.
- Renewal rules are canonical in MVP:
  - active subscription renewed early extends from `current_period_end`.
  - expired or missing subscription starts from `now`.
  - same succeeded payment cannot extend period twice.
- Duplicate notifications must not duplicate activation or extend period twice.

### 6) Expiration
- Subscription becomes expired when `current_period_end < now` and no successful renewal.
- Access checks must evaluate active window each time through one domain decision point.

## Domain Model

### `billing_tariffs`
Purpose: catalog of billable plans.
Key fields (logical):
- `id`
- `code` (unique business key)
- `name`
- `price_minor`
- `currency`
- `period_days`
- `is_active`

### `billing_subscriptions`
Purpose: specialist subscription aggregate state.
MVP cardinality and snapshot invariants:
- one specialist has at most one current subscription aggregate snapshot row in MVP.
- this table stores current subscription aggregate snapshot only.
- historical payment attempts are stored in `billing_payments`.
- historical billing-driven access state transitions are stored in `billing_access_log`.
Key fields:
- `id`
- `specialist_id` (unique in MVP aggregate model)
- `tariff_id`
- `status` (`inactive|pending_payment|active|grace|expired|canceled`)
- `current_period_start`
- `current_period_end`
- `last_payment_id`

### `billing_payments`
Purpose: payment attempts and final outcomes.
Key fields:
- `id`
- `specialist_id`
- `subscription_id` (nullable for first payment)
- `provider` (`yookassa`)
- `provider_payment_id`
- `idempotence_key`
- `amount_minor`
- `currency`
- `status` (`new|pending|waiting_for_capture|succeeded|canceled|refunded|error`)
- `created_at`, `updated_at`

### `billing_webhook_events`
Purpose: immutable inbound event log.
Key fields:
- `id`
- `provider`
- `provider_event_id` (primary dedupe key when provider event identity is available)
- `dedupe_hash` (stable hash derived from raw webhook envelope/payload when provider event identity is unavailable)
- `provider_payment_id`
- `event_type`
- `payload_json`
- `received_at`
- `processed_at`
- `processing_status`

### `billing_access_log`
Purpose: audit log of billing-driven access state transitions (not per-request access-gating decisions).
MVP note:
- per-request access decision tracing is out of scope for this table and belongs to a future observability artifact.
Key fields:
- `id`
- `specialist_id`
- `from_access_state`
- `to_access_state`
- `reason_code`
- `subscription_id`
- `changed_at`

## Status Model / State Transitions
Canonical payment statuses (MVP):
- `new|pending|waiting_for_capture|succeeded|canceled|refunded|error`

Payment transitions:
- `new -> pending|error`
- `pending -> waiting_for_capture|succeeded|canceled|error`
- `waiting_for_capture -> succeeded|canceled|error`
- `succeeded -> refunded` (status exists for forward compatibility; refund workflow is outside MVP until dedicated refund story/epic)
- Terminal states in MVP processing: `succeeded|canceled|refunded|error`
- Terminal-to-terminal transitions are forbidden except `succeeded -> refunded`.

Canonical subscription statuses (MVP):
- `inactive|pending_payment|active|grace|expired|canceled`

Subscription transitions:
- `inactive -> pending_payment` (payment started)
- `pending_payment -> active` (payment succeeded)
- `pending_payment -> inactive` (payment canceled/error)
- `active -> active` (successful early renewal extends period)
- `active -> grace` (optional grace window if explicitly enabled)
- `active|grace -> expired` (period/grace end reached)
- `expired -> pending_payment` (renewal started)
- `expired -> active` (renewal succeeded)
- `active|grace|expired -> canceled` (manual/admin cancellation flow when introduced)

## Idempotency Rules
- Outbound payment creation uses deterministic idempotence key per payment intent.
- Webhook ingestion deduplicates by provider event identity (or stable payload hash fallback).
- Subscription update command is idempotent: same succeeded payment cannot extend period more than once.
- Replayed webhook updates processing metadata but not business result.

## Security Rules
- YooKassa secret keys are backend-only and never exposed to frontend or docs examples.
- Validate webhook authenticity before mutating billing domain state.
- Enforce least-privilege access for billing/admin endpoints.
- Do not log full sensitive payload fragments beyond required audit subset.
- Keep payment/provider identifiers safe for support use, but never log credentials.

## Logging and Audit Requirements
- Correlate logs by `specialist_id`, internal `payment_id`, provider `payment_id`, and webhook event id.
- Store immutable webhook raw payload snapshots in `billing_webhook_events`.
- Record billing-driven access state transitions in `billing_access_log` for support disputes.
- Track state transition actor (`system_webhook`, `system_scheduler`, `manual_admin` when added).

## Failure Scenarios and Recovery Rules
- Provider API timeout on payment creation is an ambiguous outcome: keep local payment in non-terminal in-flight state (`new` or `pending`, depending on whether a provider acknowledgement was received), then reconcile via idempotent retry and webhook/provider-reference checks.
- Webhook delivery delay: UI stays pending; no optimistic activation via `return_url`.
- Duplicate webhook delivery: accepted but produces no duplicate state transition.
- Out-of-order events: ignore invalid backward transitions and log anomaly.
- Temporary DB failure during webhook processing: retry from queue/retry policy with idempotent guards.

## UX Notes for Specialist Owner Panel
- Billing page states: no subscription, active until date, expired, payment in progress.
- After returning from YooKassa, show "Awaiting confirmation" until backend confirms final state.
- Renewal CTA remains visible for expired and soon-to-expire subscriptions.
- All paid-feature checks route through one domain access decision point to avoid inconsistent UI/API behavior.

## QA Coverage Scope
- Payment creation happy path and retry/idempotence behavior.
- `return_url` cannot activate subscription without webhook-confirmed success.
- Webhook signature/auth checks and rejection of invalid requests.
- Duplicate webhook handling without duplicate activation.
- Access gating consistency across APIs and UI using the same domain decision point.
- Expiration and post-expiration denial behavior.
- Observability assertions: required logs/events generated for support.

## Role-based MVP Review

### Architect review
Concern: prevent coupling provider callbacks directly to feature toggles.
Approved constraint: all access decisions must use billing domain aggregate, not transport events.

### Data architect review
Concern: duplicate source-of-truth risk between provider status and local subscription.
Approved constraint: provider is external signal; local DB state is authoritative for access.

### UX review
Concern: false-positive success on return from payment page.
Approved constraint: `return_url` is informational; confirmed status shown only after backend state transition.

### Developer review
Concern: race conditions between manual polling and webhook updates.
Approved constraint: idempotent commands + transition guards + terminal-state protection.

### QA review
Concern: regressions from duplicate/out-of-order notifications.
Approved constraint: explicit tests for replayed events and forbidden back-transitions.

### Security review
Concern: secret leakage and forged webhook requests.
Approved constraint: backend-only keys, authenticated webhook validation, minimal sensitive logging.

## Manual Actions / YooKassa Cabinet Dependencies
- US-PAY-0: no manual YooKassa actions required.
- US-PAY-1: no manual YooKassa actions required.
- US-PAY-2 / US-PAY-3: manual retrieval/configuration of `shopId` and secret key required.
- US-PAY-4: manual webhook registration/configuration required.
- US-PAY-9: separate legal/compliance/fiscalization actions likely required.

## Support and Troubleshooting Source of Truth
For disputes such as "specialist paid but access not activated", investigate in this order:
1. local `billing_subscriptions` state.
2. local `billing_payments` state.
3. `billing_webhook_events` raw payload and `processing_status`.
4. provider payment reference check (YooKassa payment id/cabinet view).
5. billing audit/access logs (`billing_access_log`).

## Pre-production Readiness Checklist
- YooKassa secrets obtained and stored server-side only.
- Webhook endpoint URL is defined.
- `return_url` is defined.
- Environment separation for test and production credentials is documented.
- Billing support logging is enabled.
- Manual test cases for payment, webhook, renewal, and access gating are defined.

## Future Extensions
- Receipts / 54-FZ stream: separate implementation epic with compliance-specific acceptance criteria.
- Autopay phase 2: tokenized recurring model, mandate lifecycle, and charge retries.
- Refunds: full/partial refund lifecycle and subscription rollback policy.
- Promo codes: pre-payment price adjustment with audit traceability.
- Admin reconciliation: tools for mismatch detection between provider events and local states.
