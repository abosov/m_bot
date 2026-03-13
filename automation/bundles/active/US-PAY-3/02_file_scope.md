# US-PAY-3 File Scope

## Files Allowed to Change
- backend API route files related to specialist billing/payment start
- backend billing application/service layer files required to start payment
- backend schemas/dto files required for request/response contract
- backend tests for payment-start API and related service behavior
- billing/YooKassa documentation files only if required to keep docs in sync with implementation
- active story bundle files for `US-PAY-3`

## Likely Candidate Files
- `backend/api/...` files related to authenticated specialist actions
- `backend/services/...` files for billing orchestration
- `backend/schemas/...` or equivalent DTO/response model files
- `tests/...` route/service tests for billing start flow
- `docs/20_product/user_stories/EPIC_BILLING_YOOKASSA_MVP.md` only if acceptance wording needs sync
- `docs/50_integrations/yookassa.md` only if implementation-facing notes must be clarified
- `automation/bundles/active/US-PAY-3/*`

## Files/Layers That Must Not Be Changed
- unrelated frontend UI code
- webhook ingestion logic planned for `US-PAY-4`
- subscription lifecycle activation logic planned for `US-PAY-5`
- access gating logic planned for `US-PAY-6`
- unrelated auth, calendar, booking, public-site, or media flows
- infra/deploy files unless a blocker is discovered
- database schema beyond what already exists from prior billing stories unless an actual missing field is proven

## Change Rules
- Minimal patch only
- No unrelated refactor
- No formatting-only edits
- No new files unless strictly necessary
- Do not touch files outside the allowed scope
