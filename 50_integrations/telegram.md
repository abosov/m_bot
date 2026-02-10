# Telegram Integration (MVP)

Документ описывает интеграцию с Telegram:
- модель multi-bot через webhooks
- подключение personal bot в онбординге
- маршрутизацию updates
- минимальные практики UX и защиты от дублей

---

## 1. Концепция multi-bot

В системе есть:
- `master_bot` — единый бот платформы для онбординга specialist
- `personal bots` — отдельный Telegram-бот для каждого specialist

Все боты обслуживаются одним backend-сервисом.
Polling используется только для master_bot (реализовано).
personal bots работают через webhook `/tg/webhook/{bot_id}/{secret}` (реализовано).

---

## 2. Webhook схема

### 2.1 URL
Webhook URL для personal bot:
`/tg/webhook/{bot_id}/{secret}`

Где:
- `bot_id` — значение Telegram `getMe.id`
- `secret` — сгенерированный backend секрет, сохранённый в БД

### 2.2 Установка webhook
При онбординге (US-01) backend:
1) получает `bot_id` через `getMe`
2) генерирует `secret`
3) вызывает `setWebhook`:
   - url = `https://{BASE_URL}/tg/webhook/{bot_id}/{secret}`

Для production:
- `BASE_URL = https://api.zumbot.ru` (без слеша в конце)

Примечание:
- master_bot в текущем MVP работает в режиме polling и не использует webhook.

### 2.3 Проверка webhook запроса
При входящем запросе backend:
- находит `telegram_bot` по `bot_id`
- сравнивает `secret`
- если не совпало → отклоняет (403/404)
- если совпало → принимает update

### 2.4 Welcome message after onboarding (best-effort)
После успешного завершения онбординга specialist в master bot backend:
- переводит specialist в `active` и отправляет итоговое сообщение с deep-link на personal bot;
- дополнительно делает попытку отправить welcome-сообщение уже через personal bot.

Ключевые гарантии и поведение:
- отправка welcome является `non-blocking`: отсутствие welcome-сообщения не означает провал онбординга;
- используется короткий сетевой таймаут и ограниченное число ретраев, чтобы не задерживать основной UX;
- для отправки выбирается самый актуальный `active` personal bot специалиста
  (детерминированно: по `updated_at` по убыванию, затем по `created_at` по убыванию);
- ошибки welcome логируются с операционным контекстом (`specialist_id`, `bot_user_id`/`bot_username`),
  но без секретов (`bot_token`, `refresh_token`, `secret`).

---

## 3. Валидация bot_token (подключение specialist bot)

Backend принимает `bot_token` от specialist и выполняет:
- `getMe` (Telegram Bot API)

Если `getMe` не успешен:
- считать токен неверным
- попросить повторить ввод

Если успешен:
- сохраняем `bot_user_id`, `bot_username`, `bot_name`
- сохраняем токен зашифрованно

---

## 3.1 Проверка статуса personal bot (/status)

Master bot поддерживает команду `/status`, которая:
- находит specialist по `tg_user_id`
- расшифровывает сохранённый токен
- выполняет `getMe` с таймаутом 2–3 секунды и 1 retry

Результаты проверки:
- OK → бот отвечает, отдаём username/id
- UNAUTHORIZED → токен недействителен или бот удалён
- TEMP_ERROR → временные ошибки сети / 429 / 5xx

---

### 3.2 Обновление токена уже зарегистрированного personal bot
Если `bot_user_id` уже есть в системе:
- если бот принадлежит **тому же** specialist (`existing_bot.specialist_id == current_specialist_id`) — обновление разрешено:
  - токен перешифровывается и сохраняется,
  - `webhook_secret` ротируется,
  - `webhook_url` и `status=active` обновляются,
  - webhook переустанавливается в Telegram;
- если бот принадлежит **другому** specialist — обновление блокируется с понятным сообщением.

Логи аудита ведутся по `specialist_id/bot_user_id`, без логирования токенов и секретов.

## 4. Маршрутизация updates

### 4.1 Master bot vs personal bot
- **master_bot**: polling в процессе `main.py` (aiogram Dispatcher master).
- **personal bot**: webhook endpoint в `web_server.py`, затем передача в отдельный Dispatcher (`services/telegram/personal_dispatcher.py`).

### 4.2 Что происходит на webhook
1) backend валидирует `bot_id + secret` и `status=active`;
2) парсит JSON update в aiogram `Update`;
3) передаёт update в personal Dispatcher;
4) отвечает `200 OK` максимально быстро.

### 4.3 Минимальный обработчик personal bot
Сейчас реализован базовый `/start` handler:
- ответ: `Бот подключен. Скоро здесь появится запись/вопросы.`
- цель: подтверждение, что webhook и роутинг работают end-to-end.

### 4.4 Personal bot role detection (owner vs client)
В personal dispatcher на каждый update дополнительно формируется контекст:
- `specialist_id` — берется из `telegram_bot.specialist_id`;
- `owner_tg_user_id` и `public_name` — загружаются из `specialist_profile`;
- `sender_id` — из update (`message.from.id`, `callback_query.from.id` и др.);
- `actor`:
  - `specialist`, если `sender_id == owner_tg_user_id`;
  - `client` в остальных случаях.

Контекст пробрасывается в handlers через `data` aiogram:
`actor`, `specialist_id`, `owner_tg_user_id`, `public_name`.

Реализован короткий in-memory TTL-кэш профиля (несколько секунд) только для снижения числа запросов к БД. Источник истины — БД.

### 4.5 Ролевая модель и централизованный role-guard в personal bot
В personal bot обработчики разделены по роутерам:
- `handlers/personal_bot/routers/specialist/` — specialist-only команды;
- `handlers/personal_bot/routers/client/` — client команды/заглушки;
- `handlers/personal_bot/routers/common/` — общие команды (например `/start`).

На specialist router централизованно подключён middleware role-guard.
Это означает:
- любой update с `actor != specialist`, попавший в specialist handler, блокируется автоматически;
- в handler-ах specialist не дублируются проверки роли;
- даже если в конкретном handler забыли локальную проверку, client всё равно не попадёт в specialist-flow.

Поведение при нарушении роли:
- client получает дружелюбный ответ: «Команда доступна только специалисту.»;
- событие логируется на уровне `info/debug` как штатный отказ доступа;
- исключения наружу не выбрасываются.

Сейчас в personal bot реализовано:
- `/start` (common):
  - для owner (`actor=specialist`) — «Панель специалиста»;
  - для остальных (`actor=client`) — клиентская заглушка «Запись скоро»;
- `/status` (и текст «Мой статус») в specialist router:
  - `specialist.status`,
  - username personal bot,
  - статус Google OAuth,
  - `calendar_id`/`calendar_summary`,
  - `last_smoke_test_status`;
- `/help`:
  - specialist router — список команд specialist;
  - client router — клиентская заглушка.

Клиентский booking flow (US-03) в этом этапе не реализуется.


---

## 5. Обработка типов update (MVP)

### 5.1 message
Используется для:
- `/start`
- текстовых ответов (ввод display_name, заметка, команды)
- сообщений-заглушек

### 5.2 callback_query
Используется для:
- кнопок выбора слота
- кнопок retry
- кнопок отмены записи
- кнопок навигации (неделя вперёд / назад)

Рекомендация MVP:
- быстро отвечать `answerCallbackQuery`
  (например “Оформляю запись…”)

---

## 6. UX-минимум для предотвращения дублей

Возможны:
- двойной клик
- повторная доставка callback
- повторный запрос пользователя

Используем:
1) Idempotency в БД (`appointment.idempotency_key`)
2) UX-приёмы:
   - отвечать на callback_query
   - при необходимости гасить клавиатуру (`editMessageReplyMarkup`)

---

## 7. Rate limits и устойчивость (MVP)

Telegram ожидает быстрый ответ `200 OK`.

В MVP допустимо выполнять логику синхронно при условии:
- конкурентного backend,
- таймаутов на Google API,
- общего времени обработки ≤ 8–10 секунд.

---

## 8. Данные Telegram, которые сохраняем

### Specialist
- `tg_user_id`
- `tg_username`
- `first_name`
- `last_name`  
(через master_bot)

### Client
- `tg_user_id`
- `tg_username`
- `display_name`

Запрещено:
- сохранять телефон
- хранить полную переписку

---

## 9. Обработка ошибок и заглушки (MVP)

### 9.1 Типовые ошибки
- неверный bot_token → “проверьте токен”
- webhook не установился → “попробуйте ещё раз позже”

### 9.2 Устаревшие кнопки
Callback payload должен содержать идентификатор действия
(`appointment_id` или `start_at_utc`).

Если payload не соответствует актуальному состоянию:
- сообщение: “Кнопка устарела, обновите список слотов”
- booking_state не изменяется
- действие не выполняется

---

## 10. Сценарий «Написать специалисту» (MVP)

При ошибке бронирования или спорной ситуации клиенту показывается кнопка:
- `Написать специалисту`

Реализация:
- если у specialist есть `owner_tg_username`,
  кнопка ведёт на `https://t.me/{owner_tg_username}`
- если username отсутствует:
  бот показывает сообщение с рекомендацией
  связаться с specialist напрямую привычным способом

Платформа не передаёт и не хранит сообщения.


## 11. Проверка работы webhook (ручная)

1) Пройти онбординг в master bot до шага ввода `bot_token`.
2) Убедиться, что backend успешно вызвал `setWebhook` для personal bot.
3) Проверить в БД, что есть запись `telegram_bot` со `status=active` и `webhook_url` вида `/tg/webhook/{bot_id}/{secret}`.
4) Написать `/start` в personal bot.
5) Ожидать ответ: `Бот подключен. Скоро здесь появится запись/вопросы.`
6) Проверить логи backend: должны быть записи с `bot_id`, `specialist_id`, `update_id`, `update_type`.

Для ручного HTTP smoke-теста можно отправить update напрямую:

```bash
curl -i -X POST "${BACKEND_BASE_URL}/tg/webhook/{bot_id}/{secret}" \
  -H "Content-Type: application/json" \
  -d '{"update_id": 1, "message": {"message_id": 1, "date": 1730000000, "chat": {"id": 1, "type": "private"}, "text": "/start"}}'
```

Ожидается `200 OK` при валидном секрете и `404` при невалидном.
