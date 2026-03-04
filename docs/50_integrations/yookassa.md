# YooKassa integration (subscription billing)

## Scope
Интеграция покрывает создание платежа, редирект пользователя в YooKassa и приём webhook.

## Key principles
- Источник идентификации: только Telegram (`tg_user_id`) + `specialist_id`.
- На сайте **нет регистрации/аккаунтов**.
- Оплата связана с one-time `pay_token` (raw token в URL, hash в БД).
- `pay_token` имеет TTL (30 минут) и одноразовое использование.

## Components
- `services/billing/subscriptions.py`
  - создание `billing_purchase`
  - генерация/хэширование токена
  - обработка webhook-статусов
- `services/integrations/yookassa_client.py`
  - вызов YooKassa API (`/v3/payments`)
  - `Idempotence-Key` для create payment
- `web_server.py`
  - `/pay`
  - `/pay/confirm`
  - `/api/billing/yookassa/create`
  - `/api/billing/yookassa/webhook`

## Create payment flow
1. Пользователь в master-bot выбирает тариф/период.
2. Бэкенд создаёт `billing_purchase` со статусом `pending`.
3. Генерируется `raw pay_token`, в БД сохраняется только `pay_token_hash`.
4. Пользователю отдаётся URL `/pay?token=<raw_token>`.
5. `/pay/confirm` или `/api/billing/yookassa/create` создаёт payment в YooKassa.
6. `yookassa_payment_id` и `yookassa_status` сохраняются в `billing_purchase`.
7. Пользователь редиректится на `confirmation_url` YooKassa.

## Webhook flow
1. YooKassa вызывает `/api/billing/yookassa/webhook`.
2. По `object.id` (payment id) находится `billing_purchase`.
3. Обновляются `yookassa_status` и внутренний статус покупки.
4. Для `succeeded`:
   - `billing_purchase.status = succeeded`
   - `billing_purchase.used_at = now()`
   - активируется подписка в `specialist_profile` (`tariff_plan`, `tariff_period`, `tariff_last_paid_at`, `tariff_paid_until`).

## Idempotency
- Create payment: `Idempotence-Key` на каждый запрос в YooKassa.
- Webhook: обработка по `yookassa_payment_id` и текущему статусу покупки, повторные события не должны ломать состояние.

## Env vars
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_WEBHOOK_SECRET` (опциональная проверка входящего webhook)

## Operational notes
- Без настроенных `YOOKASSA_*` create payment должен возвращать контролируемую ошибку.
- Для расследований использовать `purchase_id`/`yookassa_payment_id`, не raw token.
