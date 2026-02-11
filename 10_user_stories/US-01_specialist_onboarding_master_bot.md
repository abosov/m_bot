# US-01 — Онбординг specialist через master bot (MVP)

## Статус сценария
- **Implemented (MVP):** старт онбординга, ввод публичного имени, подключение personal bot, Google OAuth callback, создание календаря, выбор существующего календаря с пагинацией, smoke-test календаря, финализация с переходом в personal bot.
- **Planned/TODO:** дополнительные улучшения UX/диагностики.

## Цель
Позволить специалисту завершить onboarding в master bot до состояния `specialist.status=active`,
когда personal bot подключён, Google OAuth и календарь готовы, а дальше передать специалиста
в personal bot для продолжения онбординга (настройка расписания и параметров слотов).

## Основной поток
1. `/start` в master bot.
2. Ввод `public_name`.
3. Ввод токена personal bot, валидация `getMe`, установка webhook.
4. Google OAuth и обработка callback.
5. Календарный шаг:
   - создать отдельный календарь (реализовано);
   - выбрать существующий календарь (реализовано):
     - список календарей рендерится кнопками с пагинацией Prev/Next;
     - выбор календаря выполняется по индексу в state (без передачи calendar_id в callback_data);
     - после выбора запускается smoke-test (create+delete test event);
     - при неуспешном smoke-test сохраняется статус failed и предлагается повторная проверка через `calendar:smoke`;
     - доступна смена календаря через экран выбора действия (создать новый или выбрать существующий).
6. Smoke-test календаря (create+delete test event).
7. Перевод `specialist.status` в `active` только после успешного smoke-test и выдача deep-link personal bot (`?start=owner_panel`).
8. После перехода в personal bot запускается wizard базовых настроек (продолжение онбординга):
   - рабочие дни недели;
   - интервалы по дню (до 3 интервалов: утро/день/вечер);
   - длительность сессии и буфер;
   - `max_sessions_per_day` и `slot_step_min`.

## Правила готовности
Онбординг считается завершённым только если одновременно выполнены:
- есть профиль специалиста;
- подключён активный personal bot;
- Google OAuth в состоянии connected;
- выбран/создан рабочий календарь;
- `last_smoke_test_status = ok` (smoke-test календаря успешен).

Важно: `weekly_availability`, длительность, буфер и параметры слотов не являются шагом master bot —
они настраиваются в personal bot после deep-link `owner_panel`.

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


После активации master bot отправляет deep-link в personal bot: `https://t.me/<bot_username>?start=owner_panel`.
В personal bot это открывает owner panel и мастер базовых настроек расписания.
