# Telegram Integration (MVP)

## 1. Роли Telegram-ботов

### Master bot
- Назначение: onboarding специалиста и операционные команды (`/start`, `/status`).
- Режим: **polling**.
- Запуск: внутри `main.py` (`start_bot`, `Dispatcher.start_polling`).
- Важное ограничение: master bot не использует webhook в текущем MVP.

### Personal bot
- Назначение: рабочий бот специалиста для клиентских и specialist-команд.
- Режим: **webhook**.
- Endpoint: `POST /tg/webhook/{bot_id}/{secret}`.
- Обработчик webhook: `web_server.py` → `services/telegram/personal_dispatcher.py`.

## 2. Подключение personal bot в onboarding

1. Specialist передаёт bot token от BotFather в master bot.
2. Backend валидирует token через `getMe`.
3. Backend сохраняет bot metadata и token (в зашифрованном виде).
4. Backend генерирует `webhook_secret`.
5. Backend вызывает `setWebhook` на URL:
   `https://{BASE_URL}/tg/webhook/{bot_id}/{secret}`.
6. В БД фиксируется `telegram_bot.status=active`.

## 3. Проверка webhook на стороне backend

При входящем update backend:
1. Валидирует JSON payload.
2. Проверяет `bot_id + secret + status=active` в таблице `telegram_bot`.
3. При невалидных данных возвращает `404`.
4. При валидных данных передаёт update в personal dispatcher.
5. Возвращает `200`, чтобы Telegram не зацикливал retry.

## 4. Минимальный check «webhook жив»

1. Пройти onboarding до успешного шага подключения personal bot.
2. Проверить в БД, что `telegram_bot.webhook_url` заполнен и `status=active`.
3. Отправить `/start` в personal bot из Telegram клиента.
4. Проверить backend logs: должна появиться запись вида `Webhook update accepted ...`.
5. Проверить ответ personal bot пользователю.

Дополнительный ручной HTTP smoke-test:
```bash
curl -i -X POST "${BACKEND_BASE_URL}/tg/webhook/{bot_id}/{secret}" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"message_id":1,"date":1730000000,"chat":{"id":1,"type":"private"},"text":"/start"}}'
```
Ожидается:
- `200 OK` для валидного `{bot_id}/{secret}`;
- `404 Not Found` для невалидной пары.

## 5. Типовые операционные проблемы

### `setWebhook` не ставится
Проверить:
- корректность `BASE_URL` (публичный HTTPS);
- доступность endpoint снаружи;
- валидность bot token.

### Personal bot не отвечает
Проверить:
- активный webhook в БД;
- что backend отвечает по `/healthz` и `/readyz`;
- логи webhook ingress и ошибок personal dispatcher.

## 6. Planned/TODO
- Унификация health/readiness endpoint names (`/health`, `/ready`) на уровне приложения (сейчас используются `/healthz`, `/readyz`).


### Webhook payload limit
- Backend ограничивает размер body через `MAX_WEBHOOK_BODY_BYTES`.
- При превышении лимита endpoint возвращает `413 Payload Too Large`.
