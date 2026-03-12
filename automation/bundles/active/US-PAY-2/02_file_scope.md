# US-PAY-2 File Scope

## Allowed Files for Future US-PAY-2 Implementation
- `services/integrations/yookassa_client.py`
- `services/billing/subscriptions.py`
- `services/billing/__init__.py`
- `tests/test_billing_subscriptions.py`
- `tests/test_billing_subscription_flow.py`
- `docs/50_integrations/yookassa.md`
- `automation/bundles/active/US-PAY-2/*`

## Forbidden Files/Areas for Future US-PAY-2 Implementation
- `web_server.py`
- `database.py` schema definitions
- `scripts/migrations/**`
- `frontend/**`
- deploy / infra / `.github/**`

## Scope Guardrails
- No route-layer payment API changes in this story (belongs to `US-PAY-3`/`US-PAY-4`).
- No schema evolution in this story (belongs to migration-managed stories).
- Keep changes atomic and limited to payment creation adapter/service behavior.
