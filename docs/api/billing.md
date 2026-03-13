# Billing API

## Overview
Billing endpoints currently include both:
- legacy token-based checkout endpoints for the pre-existing purchase flow;
- authenticated specialist billing endpoints for the YooKassa MVP billing-domain flow.

For the YooKassa MVP, `billing_tariffs`, `billing_subscriptions`, and `billing_payments` are the source of truth for lifecycle state. `return_url` is informational only and does not activate a subscription.

## `GET /pay?token=...`
Рендерит HTML заказа подписки.

### Validation
- token должен существовать (через `pay_token_hash` lookup)
- token не просрочен (`expires_at`)
- token не использован (`used_at IS NULL`)

### Responses
- `200` — страница заказа
- `404` — invalid token
- `410` — expired/used token

---

## `GET /pay/confirm?token=...`
Создаёт payment в YooKassa и редиректит пользователя на `confirmation_url`.

### Behavior
- валидирует token как в `/pay`
- создаёт payment (`capture=true`)
- сохраняет `yookassa_payment_id`, `yookassa_status`

### Responses
- `303` redirect to YooKassa confirmation URL
- `400` on business error (`invalid_token`, `token_expired`, ...)

---

## `POST /api/billing/yookassa/create`
API-вариант create payment.

### Request JSON
```json
{ "token": "<raw_pay_token>" }
```

### Response JSON
```json
{ "ok": true, "confirmation_url": "https://..." }
```

---

## `POST /api/specialist/profile/billing/subscription-payment`
Authenticated specialist endpoint that starts a YooKassa subscription payment from the billing-domain tariff catalog.

### Request JSON
```json
{
  "tariff_code": "pro-monthly",
  "return_url": "/billing/return"
}
```

### Behavior
- requires a valid specialist web session cookie;
- validates `tariff_code` against active `billing_tariffs`;
- reuses the current retriable payment intent for the same specialist/tariff context when possible;
- returns pending redirect data with YooKassa `confirmation_url`;
- does not activate subscription access from the API response or `return_url`.

### Response JSON
```json
{
  "payment_id": "uuid",
  "tariff_code": "pro-monthly",
  "payment_status": "pending",
  "requires_redirect": true,
  "confirmation_url": "https://..."
}
```

---

## `POST /api/billing/yookassa/webhook`
Принимает webhook от YooKassa.

### Security
- если задан `YOOKASSA_WEBHOOK_SECRET`, ожидается заголовок:
  - `X-Zumbot-Webhook-Secret: <secret>`

### Processing
- найти purchase по `object.id` (`yookassa_payment_id`)
- обновить внутренний статус purchase
- legacy purchase flow may update legacy purchase/profile state;
- YooKassa MVP specialist billing flow treats webhook-confirmed billing-domain transitions as the future source of truth for success handling.

### Response JSON
```json
{ "ok": true, "status": "succeeded" }
```
