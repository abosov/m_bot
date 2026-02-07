# US-01 — Онбординг specialist через master_bot (MVP)

## Цель
Позволить специалисту самостоятельно подключиться к платформе:
- зарегистрироваться как specialist,
- подключить личный Telegram-бот,
- авторизоваться в Google,
- выбрать или создать календарь,
- задать базовые параметры для приёма клиентов.

Онбординг выполняется **только** через master_bot.

---

## Акторы
- specialist
- master_bot
- backend
- Google OAuth / Google Calendar API
- Telegram Bot API

---

## Preconditions
- backend развёрнут и принимает webhooks
- master_bot настроен и подключён к backend
- у specialist есть Google аккаунт
- у specialist есть возможность создать Telegram-бота через BotFather

---

## Основной поток

### Шаг 1 — Старт онбординга
**specialist**
- открывает master_bot
- отправляет `/start`
- нажимает кнопку «Подключить сервис / Стать специалистом»

**backend**
- создаёт или находит запись `specialist`
- создаёт связь с Telegram-аккаунтом specialist
- устанавливает `specialist.status = onboarding`

**Данные**
- создаётся `specialist`
- создаётся `specialist_auth_telegram`

---

### Шаг 2 — Базовая информация specialist
**specialist**
- вводит публичное имя (как отображаться клиентам)

**backend**
- сохраняет публичное имя

**Данные**
- обновляется `specialist_profile.public_name`

---

### Шаг 3 — Подключение личного Telegram-бота
**specialist**
- создаёт бота через BotFather
- передаёт `bot_token` в master_bot

**backend**
1. валидирует токен через Telegram API (`getMe`)
2. получает:
   - `bot_user_id`
   - `bot_username`
   - `bot_name`
3. генерирует `webhook_secret`
4. сохраняет данные бота
5. устанавливает webhook:
   `/tg/webhook/{bot_user_id}/{webhook_secret}`

**Ошибки (MVP-обработка)**
- неверный токен → сообщение с просьбой повторить
- webhook не установился → сообщение-заглушка + возможность повторить

**Данные**
- создаётся `telegram_bot`
- `telegram_bot.status = active | error`

---

### Шаг 3.1 — Проверка доступности personal bot (/status)
**specialist**
- отправляет команду `/status` в master_bot

**backend**
- находит `specialist` по `tg_user_id`
- расшифровывает токен бота
- выполняет `getMe` с таймаутом 2–3 секунды и 1 retry

**Ответы**
- OK → “✅ Бот доступен: @username (id=...)”
- UNAUTHORIZED → “❌ Токен бота недействителен или бот удалён. Обновите токен через /start”
- TEMP_ERROR → “⚠️ Временно не удалось проверить бота. Повторите позже.”

---

### Шаг 4 — Подключение Google аккаунта
**specialist**
- нажимает «Подключить Google Calendar»
- проходит OAuth авторизацию

**backend**
1. инициирует OAuth с `offline access`
2. принимает callback
3. сохраняет `refresh_token`

**Ошибки (MVP)**
- отказ в доступе → сообщение-заглушка с рекомендацией повторить

**Данные**
- создаётся или обновляется `google_oauth`

---

### Шаг 5 — Выбор или создание календаря
**specialist**
- выбирает существующий календарь из списка  
  **или**
- создаёт новый календарь

**backend**
- при выборе:
  - сохраняет `calendar_id`
- при создании:
  - создаёт календарь через Google API
  - сохраняет `calendar_id`

**Timezone**
- backend считывает timezone календаря
- устанавливает `specialist_timezone` = timezone календаря
- если ранее был задан другой timezone — фиксирует изменение и информирует specialist

**Данные**
- создаётся `specialist_calendar`
- обновляется `specialist_profile.specialist_timezone`

---

### Шаг 6 — Настройка расписания (weekly availability)
**specialist**
- задаёт рабочие дни недели
- для каждого дня указывает:
  - 1 или 2 интервала времени

**backend**
- сохраняет weekly availability

**Данные**
- создаются/обновляются записи `weekly_availability`

---

### Шаг 7 — Завершение онбординга
**backend**
- проверяет, что:
  - личный бот подключён и активен
  - Google OAuth выполнен
  - календарь выбран
  - weekly availability задано
- устанавливает `specialist.status = active`
- сообщает specialist, что сервис готов к использованию
- отдаёт ссылку на личного бота

---

## Постусловия
- specialist полностью готов принимать записи клиентов
- личный Telegram-бот работает и подключён к backend
- Google Calendar подключён и выбран
- базовые настройки заданы

---

## Ограничения MVP
- один владелец specialist (`owner_tg_user_id`)
- повторная авторизация Google выполняется вручную через тот же сценарий
- детальная обработка ошибок и диагностика отложены

---

## Связанные документы
- `00_overview/README.md`
- `00_overview/glossary.md`
- `US-02_specialist_manage_settings_in_personal_bot.md` (следующий)
