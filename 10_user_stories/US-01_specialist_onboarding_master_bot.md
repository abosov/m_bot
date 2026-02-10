# US-01 — Онбординг specialist через master bot (MVP)

## Статус сценария
- **Implemented (MVP):** старт онбординга, ввод публичного имени, подключение personal bot, Google OAuth callback, создание календаря, smoke-test календаря, финализация с переходом в personal bot.
- **Planned/TODO:** расширенный UI для выбора существующего календаря и дополнительные улучшения UX/диагностики.

## Цель
Позволить специалисту завершить onboarding в master bot до рабочего состояния personal bot и Google Calendar.

## Основной поток
1. `/start` в master bot.
2. Ввод `public_name`.
3. Ввод токена personal bot, валидация `getMe`, установка webhook.
4. Google OAuth и обработка callback.
5. Календарный шаг:
   - создать отдельный календарь (реализовано);
   - выбрать существующий календарь (planned/TODO).
6. Smoke-test календаря (create+delete test event).
7. Перевод `specialist.status` в `active` и выдача deep-link personal bot.

## Правила готовности
Онбординг считается завершённым только если одновременно выполнены:
- есть профиль специалиста;
- подключён активный personal bot;
- Google OAuth в состоянии connected;
- выбран/создан рабочий календарь;
- smoke-test календаря успешен.

## Важные edge-cases
- `refresh_token missing`:
  - с ранее сохранённым refresh token onboarding можно продолжать;
  - без сохранённого refresh token требуется переподключение Google.
- `insufficientPermissions`:
  - пользователь получает инструкцию переподключить Google с полным набором прав.

## Ручной smoke-check
1. Пройти шаги `/start` → имя → personal bot token.
2. Подключить Google.
3. Создать календарь и дождаться успешного smoke-test.
4. Проверить, что `specialist.status=active` и personal bot отвечает на `/start`.
