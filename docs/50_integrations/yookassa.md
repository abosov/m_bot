# YooKassa integration (subscription billing)

## Scope
Интеграция покрывает создание платежа, редирект пользователя в YooKassa и приём webhook.

MVP status:
- legacy token-based checkout flow still exists in runtime;
- specialist subscription MVP uses the billing-domain tables (`billing_tariffs`, `billing_subscriptions`, `billing_payments`) as the source of truth;
- `return_url` is informational only and must not be treated as payment success.

## Key principles
- Источник идентификации: только Telegram (`tg_user_id`) + `specialist_id`.
- На сайте **нет регистрации/аккаунтов**.
- Оплата связана с one-time `pay_token` (raw token в URL, hash в БД).
- `pay_token` имеет TTL (30 минут) и одноразовое использование.

## Components
- `services/billing/subscriptions.py`
  - legacy `billing_purchase` token flow
  - billing-domain payment intent creation/reuse for specialist subscription checkout
  - webhook status handling
- `services/integrations/yookassa_client.py`
  - вызов YooKassa API (`/v3/payments`)
  - `Idempotence-Key` для create payment
- `backend/api/specialist_profile_private.py`
  - `/api/specialist/profile/billing/subscription-payment`
- `web_server.py`
  - legacy `/pay`
  - legacy `/pay/confirm`
  - legacy `/api/billing/yookassa/create`
  - `/api/billing/yookassa/webhook`

## Create payment flow
Specialist MVP flow:
1. Authenticated specialist calls `/api/specialist/profile/billing/subscription-payment`.
2. Backend validates `tariff_code` against active `billing_tariffs`.
3. Backend reuses the current retriable payment intent for the same specialist/tariff context when possible.
4. Billing-domain payment intent creation stores or reuses `billing_payments` and calls YooKassa with provider idempotence key.
5. API returns `payment_status=pending`, `requires_redirect=true`, and YooKassa `confirmation_url`.
6. Frontend redirects specialist to `confirmation_url`.
7. Return to `return_url` remains pending/checking until backend receives final confirmation via webhook.

Legacy token flow:
1. Пользователь в master-bot выбирает тариф/период.
2. Бэкенд создаёт `billing_purchase` со статусом `pending`.
3. Генерируется `raw pay_token`, в БД сохраняется только `pay_token_hash`.
4. Пользователю отдаётся URL `/pay?token=<raw_token>`.
5. `/pay/confirm` или `/api/billing/yookassa/create` создаёт payment в YooKassa.
6. `yookassa_payment_id` и `yookassa_status` сохраняются в `billing_purchase`.
7. Пользователь редиректится на `confirmation_url` YooKassa.

## Webhook flow
1. YooKassa вызывает `/api/billing/yookassa/webhook`.
2. Webhook is the source of truth for payment success confirmation in the specialist MVP flow.
3. Specialist payment-start API and `return_url` must not activate subscription access.
4. Legacy purchase flow may continue to update `billing_purchase` until later migration stories complete.

## Idempotency
- Create payment: `Idempotence-Key` на каждый запрос в YooKassa.
- Specialist payment-start endpoint reuses the latest retriable `billing_payments` record for the same specialist/tariff context to avoid uncontrolled parallel payment attempts.
- Webhook: обработка по `yookassa_payment_id` и текущему статусу покупки, повторные события не должны ломать состояние.

## Env vars
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_WEBHOOK_SECRET` (опциональная проверка входящего webhook)

## Operational notes
- Без настроенных `YOOKASSA_*` create payment должен возвращать контролируемую ошибку.
- Для расследований использовать `purchase_id`/`yookassa_payment_id`, не raw token.
