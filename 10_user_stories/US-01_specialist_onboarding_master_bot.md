# US-01 — Онбординг specialist через master_bot (MVP)

## Цель
Позволить специалисту полностью завершить онбординг в master bot:
- зарегистрироваться как specialist,
- подключить личный Telegram-бот,
- подключить Google OAuth,
- **явно** выбрать стратегию календаря (создать отдельный / выбрать существующий),
- сохранить «рабочий календарь бота», выполнить smoke-test,
- получить deep-link в personal bot.

---

## Ключевые правила
1. Один specialist = один рабочий календарь бота.
2. После OAuth календарь не выбирается автоматически.
3. MVP-путь: «Создать отдельный календарь (рекомендовано)».
4. Имя нового календаря: `Zumbot - {public_name}`.
5. Успех календарного шага: сохранён `calendar_id` + успешный smoke-test (create+delete test event).

---

## Основной поток

### Шаг 1 — Старт
- `/start` в master bot.
- Создаются `specialist` + `specialist_auth_telegram` (если это новый пользователь).

### Шаг 2 — Публичное имя
- Specialist вводит `public_name`.
- Обновляется `specialist_profile`.

### Шаг 3 — Личный Telegram-бот
- Specialist присылает токен от BotFather.
- Backend валидирует токен, ставит webhook, создаёт `telegram_bot` (`active`).

### Шаг 4 — Google OAuth
- Specialist нажимает «Подключить Google Календарь».
- Callback сохраняет refresh_token в `google_oauth`.
- Если scope недостаточен — специалист получает понятную инструкцию о переподключении.

### Шаг 5 — Календарь (новый этап)
После OAuth в master bot показывается выбор:
- `Создать отдельный календарь (рекомендовано)` — **MVP реализован полностью**.
- `Выбрать существующий календарь` — non-MVP (UI пока заглушка, но сервисные методы заложены).

#### 5.1 Создать отдельный календарь
- Backend вызывает Google `calendars.insert`.
- Сохраняет настройки в `specialist_calendar_settings`:
  - `calendar_id`, `calendar_summary`, `calendar_time_zone`, `source=created`.

#### 5.2 Smoke-test (обязательный)
- Backend создаёт тестовое событие на ближайшие ~7 минут, 5 минут длительности.
- Сразу удаляет событие.
- В `specialist_calendar_settings` пишет:
  - `last_smoke_test_at`,
  - `last_smoke_test_status` (`ok`/`failed`),
  - `last_smoke_test_error` при ошибке.

### Шаг 6 — Финализация онбординга
`specialist.status` переводится в `active`, только если:
- есть профиль,
- есть активный personal bot,
- выбран календарь,
- smoke-test успешен.

После успеха master bot отправляет:
- подтверждение,
- username personal bot,
- deep-link: `https://t.me/{personal_bot_username}`.

---

## Идемпотентность
- Если календарь уже выбран, повторно выбирать не требуется.
- `/start` показывает «Календарь подключён» + действия:
  - `Проверить доступ (smoke-test заново)`
  - `Сменить календарь` (stub до следующего релиза).

---

## Проверка вручную (smoke-инструкция)
1. Пройти `/start` → имя → токен personal bot.
2. Подключить Google OAuth.
3. Нажать «Создать отдельный календарь».
4. Убедиться:
   - `specialist.status = active`,
   - пришло сообщение с deep-link personal bot,
   - в Google появился календарь `Zumbot - {public_name}`,
   - тестового события не осталось.
