# Secrets and tokens (billing)

## Core rules
- Raw `pay_token` используется только как одноразовый маркер в URL.
- В БД хранится только `pay_token_hash` (SHA-256 + server pepper).
- Raw token, YooKassa secrets и webhook secrets нельзя логировать.

## Token model
- one-time token
- TTL: 30 минут
- после успешной обработки помечается как использованный (`used_at`)

## Secrets
- `YOOKASSA_SHOP_ID`
- `YOOKASSA_SECRET_KEY`
- `YOOKASSA_WEBHOOK_SECRET`
- pepper для hash: server-side secret (не в клиенте)

## Logging policy
- Можно логировать: `purchase_id`, `specialist_id`, `tg_user_id`, `yookassa_payment_id`, статусы.
- Нельзя логировать:
  - raw `pay_token`
  - `YOOKASSA_SECRET_KEY`
  - полный webhook payload с чувствительными полями

## Rotation and incident response
- При компрометации ключей:
  1. немедленно заменить `YOOKASSA_SECRET_KEY` и `YOOKASSA_WEBHOOK_SECRET`
  2. перезапустить сервис
  3. мониторить ошибки create/webhook
- При подозрении на утечку token URL:
  - полагаться на TTL + one-time semantics
  - при необходимости выставлять `expired` для уязвимых purchase.

## Identity statement
Сайт Zumbot не имеет регистрации. Пользовательская идентификация в оплате выполняется через Telegram-контекст (`tg_user_id`) и одноразовый `pay_token`.
