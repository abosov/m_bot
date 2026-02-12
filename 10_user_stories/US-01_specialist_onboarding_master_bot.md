# US-01 — Онбординг specialist через master bot (MVP)

## Статус сценария
- **Implemented (MVP):** старт онбординга, ввод публичного имени, подключение personal bot, Google OAuth callback, создание календаря, выбор существующего календаря с пагинацией, smoke-test календаря, финализация с переходом в personal bot.
- **Planned/TODO:** дополнительные улучшения UX/диагностики.

## Цель
Позволить специалисту завершить onboarding в master bot до состояния `specialist.status=active`,
когда personal bot подключён, Google OAuth и календарь готовы, затем автоматически применить стартовые настройки специалиста
и передать специалиста в personal bot для возможного редактирования.

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
7. После успешного smoke-test система автоматически применяет дефолты (идемпотентно, только если значения отсутствуют):
   - `specialist_timezone`: timezone выбранного Google Calendar, fallback `UTC`;
   - weekly availability: Пн–Пт рабочие, Сб–Вс выходные, интервалы `09:00–12:00`, `13:00–17:00`, `17:00–21:00`;
   - параметры профиля: duration=60, buffer=10, cancel_window=12h, max/day=4, slot_step=15 (`{60,30,15,10}`).
8. Затем `specialist.status` переводится в `active` и выдаётся deep-link personal bot (`?start=owner_panel`) для редактирования уже применённых настроек.
9. В этот момент фиксируется двухфазный статус онбординга: `onboarding_master_completed_at=now()`, `onboarding_personal_completed_at=NULL`.
10. При первом входе в personal bot (`/start` и `?start=owner_panel`) показывается экран продолжения онбординга с дефолтами и кнопками: изменить / оставить как есть / позже.
11. Кнопка «Оставить как есть» проставляет `onboarding_personal_completed_at=now()` и открывает owner panel.

## Правила готовности
Онбординг считается завершённым только если одновременно выполнены:
- есть профиль специалиста;
- подключён активный personal bot;
- Google OAuth в состоянии connected;
- выбран/создан рабочий календарь;
- `last_smoke_test_status = ok` (smoke-test календаря успешен).

Важно: master bot не проводит опрос по этим настройкам, а только авто-применяет стартовую конфигурацию после smoke-test.
Редактирование остаётся в personal bot (`owner_panel`) после активации specialist.

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
В personal bot это открывает owner panel, показывает уже применённые значения и предлагает изменить их.
