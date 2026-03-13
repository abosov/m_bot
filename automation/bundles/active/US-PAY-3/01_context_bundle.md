# US-PAY-3 Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`
- `automation/bundles/active/US-PAY-1/*`
- `automation/bundles/active/US-PAY-2/*`

## Current Code Reality
- Billing domain source of truth for MVP is the new billing domain introduced in `US-PAY-1`.
- YooKassa provider adapter and payment creation service were added in `US-PAY-2`.
- Legacy billing runtime still exists via `BillingPurchase` and `SpecialistProfile.tariff_*`.
- Existing `docs/50_integrations/yookassa.md` documents legacy runtime behavior and must not override the new billing-domain architecture.
- `US-PAY-3` is the first story that is allowed to expose specialist-facing runtime API for payment start.

## Target Architecture
- Add authenticated backend API endpoint for specialist subscription payment start.
- Validate requested tariff/plan against allowed subscription billing options.
- Reuse or create billing-domain payment intent through the new YooKassa payment service.
- Return redirect-oriented payload including YooKassa `confirmation_url` and pending state information.
- Keep payment state pending until webhook-confirmed transition in `US-PAY-4`.
- Treat `return_url` as informational UI-only flow, never as payment success confirmation.

## Story Boundaries
- This story owns payment-start API and redirect contract only.
- Webhook ingestion/verification/transition handling belongs to `US-PAY-4`.
- Subscription activation/renewal belongs to `US-PAY-5`.
- Access gating belongs to `US-PAY-6`.
- UI screens and payment cabinet ergonomics belong to later UI stories unless minimal API contract alignment is required.

## Risks and Controls
- Risk: accidental activation from `return_url`.
  - Control: endpoint returns pending state only; no activation logic in return flow.
- Risk: duplicate payment starts from repeated clicks/retries.
  - Control: enforce active-payment reuse or equivalent idempotent guard for same subscription context.
- Risk: legacy `BillingPurchase` path gets reused as source of truth.
  - Control: billing-domain tables remain authoritative for MVP lifecycle.
- Risk: webhook arrives later than redirect or multiple times.
  - Control: pending-until-webhook architecture remains explicit in API contract and review criteria.
- Risk: route work leaks into unrelated schema/UI areas.
  - Control: keep file scope explicit and minimal.
