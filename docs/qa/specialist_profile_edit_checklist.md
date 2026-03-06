# QA checklist: specialist profile edit (`/profile/edit`)

## Preconditions
- Specialist opens owner panel and taps callback **«✏️ Редактировать профиль специалиста»** to get a fresh link (`/profile/edit#token=...`).
- Re-tapping callback issues a new one-time link without reopening owner panel.
- Повторная регистрация specialist и reset аккаунта не требуются.
- Проверки выполняются на уже существующем specialist (existing account).
- Backend is running and private profile endpoints are available.

## Auth / session
- [ ] Opening page from bot link shows `✅ Авторизовано`.
- [ ] Opening page without valid token/session shows auth error message.
- [ ] Для `expired_or_used` отображается текст: `Ссылка устарела или уже была использована. Вернитесь в бот и запросите новую.`
- [ ] При отсутствии token/hash отображается текст: `Ссылка для входа не найдена. Откройте страницу из бота.`
- [ ] Если hash-token невалиден, но `GET /connect/status` возвращает `ok=true`, страница открывается и профиль загружается.
- [ ] Hash token is removed from URL after successful consume.


## Сценарий: старая ссылка из Telegram
- [ ] Открыть свежую ссылку из бота → авторизация успешна, страница профиля загружена.
- [ ] Открыть ту же ссылку повторно в новой вкладке → отображается flow `expired_or_used` с понятным текстом про возврат в бот за новой ссылкой.
- [ ] Вернуться в бот и нажать **«✏️ Редактировать профиль специалиста»** повторно → бот выдаёт новую одноразовую ссылку, переход по ней снова успешен.
- [ ] Повторные нажатия callback **«✏️ Редактировать профиль специалиста»** не вызывают Telegram alert `can't parse entities`.
- [ ] Текст сообщения не содержит raw URL/token (`/profile/edit#token=...` только в URL-кнопке).
- [ ] Сообщение отправляется как plain text (`parse_mode` отсутствует или `None`).
- [ ] Для specialist с завершённым personal onboarding и для specialist без «свежего» onboarding используется один и тот же callback path `owner_panel:profile_edit_link`.

## Data loading
- [ ] After auth, form fields are populated from `GET /api/specialist/profile`.
- [ ] Empty values render as empty strings, no `null` shown in inputs.


## Public page block
- [ ] На странице есть секция **«Публичная страница»** сразу под статусом авторизации.
- [ ] При `is_published=false` показан бейдж `Черновик` и подсказка `Пока видите только Вы`.
- [ ] При `is_published=true` показан бейдж `Опубликовано`.
- [ ] Если `public_slug` отсутствует, показан текст `Ссылка появится после создания slug`, кнопка `Копировать` disabled.
- [ ] Если `public_slug` задан, отображается ссылка вида `https://zumbot.ru/<slug>` и активна кнопка `Копировать`.
- [ ] Кнопка `Опубликовать` вызывает publish endpoint и меняет состояние на `Опубликовано`.
- [ ] Кнопка `Снять с публикации` вызывает unpublish endpoint и меняет состояние на `Черновик`.
- [ ] Во время запроса publish/unpublish кнопка публикации disabled.
- [ ] `Копировать` работает через Clipboard API, при недоступности — через fallback.

## Block save behavior
- [ ] Для нового профиля без `public_slug` кнопки `Сохранить` для **О себе / Образование / Услуги и цены / Отзывы** disabled.
- [ ] Для нового профиля без `public_slug` кнопки `Загрузить фото` и `Загрузить документы`, а также file inputs disabled.
- [ ] При отсутствии `public_slug` видна подсказка: `Сначала сохраните основную информацию, чтобы создать ссылку профиля.`
- [ ] Кнопка `Сохранить` в блоке **Основное** остаётся активной.
- [ ] После успешного сохранения **Основное** и появления `public_slug` все secondary save/upload кнопки становятся активными без reload.
- [ ] Saving **Основное** updates name/specialization/quote.
- [ ] В блоке **«Основное»** поле **«Цитата»** визуально расположено после ФИО и специализации как отдельный подблок.
- [ ] На desktop и mobile поле **«Цитата»** остаётся ниже ФИО и специализации.
- [ ] Saving **О себе** updates only `about` in merged payload behavior.
- [ ] Saving **Образование** updates only `education`.
- [ ] Saving **Услуги и цены** updates only `services`.
- [ ] Saving **Отзывы** updates only `reviews`.
- [ ] During request, corresponding Save button is disabled.
- [ ] On success, status `Сохранено ✅` appears and hides after ~2.5s.
- [ ] Дополнительно появляется toast/label `Сохранено` на ~2.5s после успешного PUT.
- [ ] On API error, user-friendly error text appears (no traceback).

## Uploads
- [ ] Photo upload accepts jpeg/png/webp and returns success.
- [ ] Re-upload photo replaces old photo media entry.
- [ ] Document upload accepts pdf/jpeg/png.
- [ ] Selecting multiple documents uploads all files sequentially.
- [ ] Media list refreshes after upload and shows uploaded documents.
- [ ] Invalid content type or oversize file returns user-facing error.

## Security / privacy
- [ ] Media list does not expose `file_key`.
- [ ] Requests use cookie session (`credentials: include`).
- [ ] No public endpoint exposes uploaded private media directly.


## Manual smoke (existing specialist without reset)
- [ ] Взять уже существующего specialist (без reset аккаунта и без повторной регистрации).
- [ ] Открыть owner panel и нажать **«✏️ Редактировать профиль специалиста»**.
- [ ] Убедиться, что приходит новое сообщение с plain-text текстом и URL-кнопкой **«Открыть редактор профиля»**.
- [ ] Открыть ссылку и проверить, что на странице отображается `✅ Авторизовано`.
- [ ] Вернуться в бот и повторить callback ещё раз — должна прийти новая одноразовая ссылка.
