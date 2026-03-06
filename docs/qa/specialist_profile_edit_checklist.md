# QA checklist: specialist profile edit (`/profile/edit`)

## Preconditions
- Specialist has access link from personal bot (`/profile/edit#token=...`).
- Backend is running and private profile endpoints are available.

## Auth / session
- [ ] Opening page from bot link shows `✅ Авторизовано`.
- [ ] Opening page without valid token/session shows auth error message.
- [ ] Hash token is removed from URL after successful consume.

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
- [ ] Saving **Основное** updates name/specialization/quote.
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

