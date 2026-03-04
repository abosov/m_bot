# Billing API

## Overview
Billing endpoints обслуживают подписки без web-регистрации.

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

## `POST /api/billing/yookassa/webhook`
Принимает webhook от YooKassa.

### Security
- если задан `YOOKASSA_WEBHOOK_SECRET`, ожидается заголовок:
  - `X-Zumbot-Webhook-Secret: <secret>`

### Processing
- найти purchase по `object.id` (`yookassa_payment_id`)
- обновить внутренний статус purchase
- при `succeeded` активировать подписку в `specialist_profile`

### Response JSON
```json
{ "ok": true, "status": "succeeded" }
```
