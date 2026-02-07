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
Polling используется только для master_bot в текущей реализации;
personal bots планируются на webhook-схеме.

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

Примечание:
- master_bot в текущем MVP работает в режиме polling и не использует webhook.

### 2.3 Проверка webhook запроса
При входящем запросе backend:
- находит `telegram_bot` по `bot_id`
- сравнивает `secret`
- если не совпало → отклоняет (403/404)
- если совпало → принимает update

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

## 4. Маршрутизация updates

### 4.1 Определение типа бота
На входе webhook:
- если `bot_id` соответствует master_bot → маршрут в Master Bot Handler
- иначе → маршрут в Personal Bot Handler:
  - определить `specialist_id` по `telegram_bot.specialist_id`

### 4.2 Определение роли отправителя (personal bot)
- загрузить `owner_tg_user_id` из `specialist_profile`
- сравнить с `from.id` из update
- если совпало → actor = specialist
- иначе → actor = client

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
