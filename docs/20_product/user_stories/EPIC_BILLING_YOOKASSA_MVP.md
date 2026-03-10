# EPIC: YooKassa Specialist Subscription Billing MVP

## Problem Statement
Zumbot needs a reliable billing foundation for specialist paid access. Without a formal billing domain and lifecycle, access control can become inconsistent, provider callbacks can be misinterpreted, and support cannot reconcile disputes quickly.

## Business Goal
Enable specialists to purchase and renew monthly subscriptions through YooKassa in an MVP flow that is auditable, secure, and ready for iterative rollout.

## MVP Scope
- Manual monthly renewal payment flow via YooKassa hosted checkout.
- Billing domain entities for tariffs, subscriptions, payments, webhook events, and billing access-state audit (billing-driven access state transitions).
- Per-request access-decision tracing remains a future observability scope.
- Webhook-first payment confirmation with idempotent processing.
- Unified paid-feature access gating based on billing domain state.
- Minimal specialist billing UI for status + renewal actions.

## Out of Scope
- Autopay recurring charges.
- Fiscal receipts / 54-FZ implementation details.
- Refund automation.
- Promo code engine.
- Advanced finance reconciliation dashboards.

## Success Criteria
- Specialists can complete manual monthly renewal through YooKassa.
- Access is granted only after confirmed successful payment in domain state.
- Duplicate provider notifications do not cause duplicate activation.
- Support can trace payment/subscription decisions and billing-driven access state transitions via audit logs.
- Architecture supports later autopay, receipts, and reconciliation epics.

## Canonical MVP Billing Invariants
- Subscription statuses: `inactive|pending_payment|active|grace|expired|canceled`.
- Payment statuses: `new|pending|waiting_for_capture|succeeded|canceled|refunded|error`.
- Payment creation edge: local row starts as `new`, transitions to `pending` on successful provider create-payment response, transitions to `error` on provider create failure.
- `refunded` status is forward-compatible in model; refund workflow remains out of MVP until dedicated story/epic.
- One specialist has at most one current subscription aggregate in MVP.
- `billing_access_log` is an audit log of billing-driven access state transitions; per-request access-decision tracing is a future observability artifact.
- Renewal rules:
  - early renewal extends from `current_period_end`.
  - expired/missing subscription starts from `now`.
  - same succeeded payment cannot extend period twice.

---

## US-PAY-0 Documentation architecture and roadmap
- **Manual actions:** none.
- **Objective:** Publish architecture and implementation roadmap as source docs.
- **Scope:** Billing architecture doc + epic/user-story decomposition + docs indexes.
- **Non-goals:** Runtime code, schema migration, UI/API behavior changes.
- **Dependencies:** Existing Codex operating system and repository docs structure.
- **Acceptance notes:** Docs are discoverable; boundaries and constraints are explicit.
- **Implementation order:** 0 (first).

## US-PAY-1 Billing domain model
- **Manual actions:** none.
- **Objective:** Introduce billing domain persistence model.
- **Scope:** Tariffs, subscriptions, payments, webhook events, access log schema + domain invariants.
- **Non-goals:** Provider integration or UI delivery.
- **Dependencies:** US-PAY-0 architecture decisions.
- **Acceptance notes:** Schema aligns with canonical status sets, one-active-subscription invariant, and idempotency strategy.
- **Naming note:** logical idempotence key is persisted in schema as `provider_idempotence_key`.
- **Implementation order:** 1.
- **Schema source of truth artifact:** `scripts/migrations/20260316_add_billing_domain_model.sql`.
- **Legacy boundary:** `billing_purchase` + `specialist_profile.tariff_*` remain legacy artifacts and are not source of truth for YooKassa MVP lifecycle; runtime migration is deferred to follow-up stories.

## US-PAY-2 YooKassa client and payment creation service
- **Manual actions:** YooKassa cabinet required.
- **Objective:** Add backend provider adapter and payment intent service.
- **Scope:** Create-payment request/response handling, idempotence key policy, provider error mapping.
- **Non-goals:** Public API endpoint and UI wiring.
- **Dependencies:** US-PAY-1 domain model.
- **Acceptance notes:** Secret keys remain backend-only; retries are safe.
- **Implementation order:** 2.

## US-PAY-3 Payment creation API and redirect flow
- **Manual actions:** YooKassa cabinet required.
- **Objective:** Expose specialist-facing API for payment start and redirect handling.
- **Scope:** Authenticated endpoint, tariff selection validation, `confirmation_url` return payload, pending-state UX contract.
- **Non-goals:** Treating `return_url` as payment success confirmation.
- **Dependencies:** US-PAY-2 service.
- **Acceptance notes:** Return flow is informational; state remains pending until webhook-confirmed.
- **Implementation order:** 3.

## US-PAY-4 Webhook ingestion and processing
- **Manual actions:** YooKassa cabinet required.
- **Objective:** Accept YooKassa webhooks safely and idempotently.
- **Scope:** Signature/auth verification, event persistence, dedupe, transition command dispatch.
- **Non-goals:** Admin reconciliation UI.
- **Dependencies:** US-PAY-1 and US-PAY-2.
- **Acceptance notes:** Replay/duplicate notifications are no-op for applied transitions.
- **Implementation order:** 4.

## US-PAY-5 Subscription activation / renewal logic
- **Manual actions:** none.
- **Objective:** Apply payment outcomes to subscription lifecycle.
- **Scope:** Activate first subscription, extend renewals, expire subscriptions, protect terminal transitions.
- **Non-goals:** Grace/collections complexity beyond MVP rules.
- **Dependencies:** US-PAY-4 confirmed event processing.
- **Acceptance notes:** Early renewal extends from `current_period_end`; expired/missing starts from `now`; same successful payment cannot extend period twice.
- **Implementation order:** 5.

## US-PAY-6 Access gating
- **Manual actions:** none.
- **Objective:** Enforce paid access through one domain decision point.
- **Scope:** Centralized access-check service used by all paid features.
- **Non-goals:** Scattershot feature-level billing checks.
- **Dependencies:** US-PAY-5 lifecycle state correctness.
- **Acceptance notes:** All paid-feature checks route through unified decision path.
- **Implementation order:** 6.

## US-PAY-7 Specialist billing UI
- **Manual actions:** none.
- **Objective:** Provide specialist owner panel billing experience.
- **Scope:** Show plan/status/expiry, start payment, show awaiting-confirmation state after return.
- **Non-goals:** Rich financial analytics.
- **Dependencies:** US-PAY-3 and US-PAY-6.
- **Acceptance notes:** UI never marks success before backend domain confirmation.
- **Implementation order:** 7.

## US-PAY-8 Billing observability / admin support
- **Manual actions:** none.
- **Objective:** Ensure operational supportability.
- **Scope:** Structured logs, correlation IDs, basic admin/support trace endpoints or views.
- **Non-goals:** Full finance back-office.
- **Dependencies:** US-PAY-4 and US-PAY-5.
- **Acceptance notes:** Support can reconstruct billing access-state transition timeline per payment/subscription.
- **Implementation order:** 8.

## US-PAY-9 Receipts / 54-FZ
- **Manual actions:** legal/compliance required.
- **Objective:** Add fiscalization-compliant receipt stream.
- **Scope:** Receipt issuance workflow and compliance states.
- **Non-goals:** Changing MVP payment confirmation model.
- **Dependencies:** US-PAY-2 and legal/compliance decisions.
- **Acceptance notes:** Clearly treated as separate implementation stream from MVP core.
- **Implementation order:** 9.

## US-PAY-10 Autopay phase 2
- **Manual actions:** none.
- **Objective:** Introduce recurring autopay lifecycle.
- **Scope:** Tokenized payment method handling, recurring charge scheduler/retries, mandate lifecycle.
- **Non-goals:** Altering manual-renewal MVP commitments retroactively.
- **Dependencies:** Stable MVP billing domain + policy/legal approval.
- **Acceptance notes:** Autopay remains an explicit phase-2 extension.
- **Implementation order:** 10.
