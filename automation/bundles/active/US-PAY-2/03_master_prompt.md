# US-PAY-2 PROMPT 2 — Implement YooKassa provider adapter and payment intent service

## ROLE
You are the System Architect + Data Architect + UX + Developer + Tech Writer + QA + Security Reviewer for Zumbot.

## TASK
Implement US-PAY-2 runtime scope only: backend provider adapter + payment intent service for YooKassa payment creation aligned with billing domain model from US-PAY-1.

## MANDATORY CONTEXT
Read and follow:
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/PROJECT_CONTEXT.md`
- `docs/90_codex/REPOSITORY_MAP.md`
- `docs/90_codex/PROJECT_CONTEXT_UPDATE_PROTOCOL.md`
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`
- `docs/30_architecture/billing_yookassa_subscription_mvp.md`
- `automation/bundles/active/US-PAY-2/00_story.md`
- `automation/bundles/active/US-PAY-2/01_context_bundle.md`
- `automation/bundles/active/US-PAY-2/02_file_scope.md`

## GOAL
Deliver a test-covered service-layer implementation for payment creation that:
- builds YooKassa create-payment requests correctly,
- persists/updates payment intent state in billing domain path,
- applies deterministic idempotence behavior,
- maps provider failures into safe internal outcomes.

## NON-GOALS
Do not:
- add or modify public/private payment API routes,
- wire frontend billing UI behavior,
- modify schema/migrations,
- migrate or refactor unrelated legacy billing flows.

## SOURCE OF TRUTH
- Architecture: `docs/30_architecture/billing_yookassa_subscription_mvp.md`
- Story boundaries: `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md`
- Process rules: `docs/90_codex/CODEX_OPERATING_SYSTEM.md`

## FILES ALLOWED TO CHANGE
- `services/integrations/yookassa_client.py`
- `services/billing/subscriptions.py`
- `services/billing/__init__.py`
- `tests/test_billing_subscriptions.py`
- `tests/test_billing_subscription_flow.py`
- `docs/50_integrations/yookassa.md` (minimal alignment note only if needed)
- `automation/bundles/active/US-PAY-2/*` (review/follow-up updates only)

## FILES NOT ALLOWED TO CHANGE
- `web_server.py`
- `database.py` schema ownership areas
- `scripts/migrations/**`
- `frontend/**`
- deploy/infra/`.github/**`
- telegram handlers

## IMPLEMENTATION RULES
- Minimal patch only.
- No unrelated refactor.
- No formatting-only edits.
- Keep legacy flow references only where needed for compatibility context.
- Do not treat `docs/50_integrations/yookassa.md` legacy flow as architecture source of truth.

## TEST PLAN
Run and report:
- `pytest tests/test_billing_subscriptions.py`
- `pytest tests/test_billing_subscription_flow.py`

## OUTPUT FORMAT
Return:
1. changed files summary
2. architecture rationale and scope compliance
3. test results
4. review classification (`MERGE BLOCKER` / `MINOR IMPROVEMENT` / `FOLLOW-UP STORY`)
5. final diff
