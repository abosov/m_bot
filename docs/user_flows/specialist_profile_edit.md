# User flow: редактирование профиля специалиста

## Статус
Рабочий flow: форма `/profile/edit` подключена к приватному API и поддерживает сохранение блоков и загрузку медиа.

## Цель
Дать специалисту безопасную точку входа из личного Telegram-бота на web-страницу редактирования профиля и сохранить draft-данные.

## Поток (фактическое поведение)
1. Специалист открывает экран настроек личного бота и нажимает кнопку **«✏️ Редактировать профиль специалиста»**.
   - Если публичная страница уже опубликована и slug валиден, в этом же меню показывается URL-кнопка **«🌐 Открыть публичную страницу»** (`https://zumbot.ru/<slug>`).
2. Бот генерирует `web_connect_token` через сервис web-connect.
3. Бот формирует URL вида `/profile/edit#token=<raw_token>` и открывает страницу сайта.
4. Frontend читает token из hash-фрагмента URL (`#token=...`, также поддерживается короткий ключ `#t=...`).
5. Если token присутствует, frontend вызывает `POST /auth/telegram/consume` с JSON `{ "token": "..." }`.
6. Backend валидирует и «поглощает» token, затем выставляет cookie `web_auth_session` (`HttpOnly`, `Secure`, `SameSite=Lax`).
7. При успешном consume frontend удаляет hash из URL (через `history.replaceState`).
8. Если token отсутствует или consume неуспешен, frontend делает fallback-проверку активной сессии через `GET /connect/status`.
9. После успешной авторизации frontend загружает draft: `GET /api/specialist/profile`.
10. Пользователь редактирует блоки и сохраняет их отдельными кнопками. На каждый save выполняется `PUT /api/specialist/profile` с полным payload (`merge` на клиенте: `{...state.model, ...patch}`).
11. Блок **«Публичная страница»** показывает статус публикации (`Черновик`/`Опубликовано`), публичную ссылку `https://zumbot.ru/<public_slug>` (если slug задан), кнопку `Копировать` и кнопку `Опубликовать`/`Снять с публикации`.
12. Кнопка публикации вызывает private API:
    - `POST /api/specialist/profile/publish`
    - `POST /api/specialist/profile/unpublish`
    Во время запроса кнопка блокируется; после ответа UI обновляется без reload.
13. Кнопка `Копировать` копирует публичную ссылку через `navigator.clipboard` с fallback на `document.execCommand('copy')`.
14. Медиа-шаги:
    - **Фото профиля**: `POST /api/specialist/profile/photo` (`multipart/form-data`, поле `file`, один файл). После успешной загрузки выполняется обновление списка медиа.
    - **Документы**: `POST /api/specialist/profile/documents` (`multipart/form-data`, поля `file` + `title`). При выборе нескольких файлов frontend отправляет последовательные запросы (по одному на файл). После загрузки выполняется обновление списка медиа.
    - **Список медиа для UI**: `GET /api/specialist/profile/media` (используется на старте страницы и после успешных upload-операций).

## Эндпоинты, реально используемые страницей `/profile/edit`
### Авторизация / сессия
- `POST /auth/telegram/consume`
- `GET /connect/status` (fallback-проверка, если нет валидного token в hash)

### Профиль
- `GET /api/specialist/profile`
- `PUT /api/specialist/profile`

### Публикация
- `POST /api/specialist/profile/publish`
- `POST /api/specialist/profile/unpublish`

### Медиа
- `POST /api/specialist/profile/photo`
- `POST /api/specialist/profile/documents`
- `GET /api/specialist/profile/media`

## UX детали
- У каждого текстового блока своя кнопка **«Сохранить»**.
- На успешном сохранении текстовых блоков показывается статус **«Сохранено ✅»** и toast **«Сохранено»** на ~2.5 секунды.
- В блоке «Публичная страница» при отсутствии slug показывается подсказка «Ссылка появится после создания slug».
- Если профиль не опубликован, показывается подсказка «Пока видите только Вы».
- При запросе соответствующая кнопка блокируется до завершения.
- Текстовые поля trim-ятся на клиенте перед отправкой.
- Ошибки показываются коротким сообщением (без stacktrace).

## Состав полей на форме
- Основное: `first_name`, `middle_name`, `last_name`, `specialization`, `hero_quote`
- Контент-блоки: `about`, `education`, `services`, `reviews`
- Медиа: фото (`photo`) и документы (`document`)

## TODO
- В текущем UI нет операций удаления/переупорядочивания документов: реализованы только загрузка и чтение списка.
