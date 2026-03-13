# US-PAY-3 PROMPT 1 — Payment Start API and Redirect Flow

## ROLE
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement US-PAY-3: add the authenticated backend API flow that starts a YooKassa subscription payment for a specialist and returns redirect-oriented confirmation data, while preserving the billing-domain architecture and keeping payment state pending until webhook confirmation.

## MANDATORY CONTEXT
Read and follow:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/30_architecture/billing_yookassa_subscription_mvp.md`
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`
- `automation/bundles/active/US-PAY-3/00_story.md`
- `aumation/bundles/active/US-PAY-3/01_context_bundle.md`
- `automation/bundles/active/US-PAY-3/02_file_scope.md`

## BEFORE IMPLEMENTING
1. Identify the exact existing files to modify.
2. Identify the exact route(s), schema(s), and service symbol(s) involved.
3. State the source of truth for billing lifecycle decisions.
4. State which files/layers must not be changed.
5. Verify whether an authenticated specialist-facing API route already exists that should be extended instead of creating a parallel path.
6. Verify router registration if a new route module is introduced.

## GOAL
End state:
- there is an authenticated specialist-facing backend endpoint to start a subscription payment
- the endpoint validates the requested tariff/plan against allowed billing-domain options
- the endpoint reuses the billing-domain payment intent service from US-PAY-2 instead of duplicating provider logic
- the response returns pending-state payment data and YooKassa `confirmation_url`
- the implementation does not treat `return_url` as payment success
- tests cover the route/service behavior for the new flow
- documentation is updated if API/runtime behavior changed

## SOURCE OF TRUTH
- `docs/30_architecture/billing_yookassa_subscription_mvp.md`
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`
- Billing-domain tables introduced in US-PAY-1 (`billing_payments`, `billing_subscriptions`, `billing_tariffs`, related billing domain artifacts)

## NON-GOALS
Do not:
- implement webhook ingestion or webhook business processing
- activate subscription access from API response, return flow, or UI state
- migrate the whole legacy billing runtime in this story
- add frontend payment UI beyond minimal contract alignment if strictly required
- introduce autopay, receipts, refunds, or unrelated billing features
- refactor unrelated auth, calendar, booking, public-site, or media code

## FILES ALLOWED TO CHANGE
- backend API route files related to authenticated specialist billing/payment start
- backend billing service/orchestration files needed for this route
- backend request/response schema files needed for this contract
- backend tests for route/service behavior
- billing docs only if needed to sync behavior
- `automation/bundles/active/US-PAY-3/*`

## FILES/LAYERS THAT MUST NOT BE CHANGED
- webhook handling logic planned for US-PAY-4
- subscription activation/renewal logic planned for US-PAY-5
- access gating logic planned for US-PAY-6
- unrelated frontend code
- infra/deploy files unless a blocker is proven
- database schema unless a truly missing field is proven and justified

## IMPLEMENTATION RULES
- Minimal patch only
- No unrelated refactor
- No formatting-only edits
- No new files unless strictly necessary
- Do not touch files outside FILES_ALLOWED_TO_CHANGE
- API endpoints must remain thin; business logic belongs in services
- Reuse existing billing payment intent service where possible
- If a new endpoint is added, verify router registration
- If docs change, update them in the same patch

## ARCHITECTURAL GUARDRAILS
- `return_url` is informational only
- webhook is the future source of truth for payment success
- API response may say pending / requires_redirect, but must not imply active subscription
- duplicate click / retry behavior must not create uncontrolled parallel active payment attempts for the same subscription context
- active/retriable billing payment behavior must remain idempotent and reviewable
- legacy `billing_purchase` flow is not the target source of truth for this MVP billing lifecycle

## TESTING
Run or update the minimum focused tests for this story.
Prefer targeted pytest scope for changed route/service behavior.

At minimum ensure coverage for:
- successful payment-start response with `confirmation_url`
- invalid or inactive tariff handling
- no activation side effect from route response
- retry/duplicate-start guard or reuse behavior, depending on chosen implementation
- route auth enforcement if there is an established repository pattern for it

## OUTPUT FORMAT
Return:
1. implementation summary
2. exact changed files
3. architecture notes
4. tests run
5. docs updated
6. final diff
