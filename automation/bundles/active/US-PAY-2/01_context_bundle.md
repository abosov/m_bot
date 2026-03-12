# US-PAY-2 Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/30_architecture/billing_yookassa_subscription_mvp.md`
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`

## Current Code Reality
- Legacy billing runtime exists via `BillingPurchase` and `SpecialistProfile.tariff_*` flow.
- Existing integration document `docs/50_integrations/yookassa.md` describes legacy runtime endpoints/flow.
- Legacy flow is operational context, but not the target architecture source of truth for MVP billing lifecycle.

## Target Architecture for US-PAY-2
- Move payment creation logic toward billing domain path centered on `billing_payments`.
- Implement provider adapter and service-level orchestration only.
- Keep route-layer integration for later stories (`US-PAY-3` and `US-PAY-4`).

## Story Boundaries
- This story is backend service/integration scope only.
- No direct route/UI behavior updates.
- No schema/migration changes (US-PAY-1 already owns domain model schema).

## Risks and Controls
- Risk: accidental reuse of legacy `billing_purchase` path as source of truth.
  - Control: treat new billing domain tables as authoritative for MVP path.
- Risk: endpoint work leaking into this story.
  - Control: keep API route changes explicitly deferred to US-PAY-3/US-PAY-4.
- Risk: ambiguous provider failures.
  - Control: require explicit provider error mapping and idempotent retry-safe behavior.

## Docs Mismatch Note
`docs/50_integrations/yookassa.md` currently documents legacy flow and should not be used as target architecture source of truth for US-PAY-2 implementation decisions.
