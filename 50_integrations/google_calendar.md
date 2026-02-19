# Google Calendar Integration (MVP)

## 1. OAuth требования

Для onboarding требуется OAuth 2.0 с offline-доступом и календарными scope.

Минимальные scope текущего MVP:
- `https://www.googleapis.com/auth/calendar.readonly` — нужен для получения списка календарей пользователя и выбора рабочего календаря (`calendarList.list`).
- `https://www.googleapis.com/auth/calendar.events` — нужен для smoke-test в выбранном календаре (`events.insert` + `events.delete`) и дальнейшего управления событиями.

Если пользователь уже выдавал доступ с меньшими правами, требуется re-consent (повторное подключение).

## 2. Callback endpoint

- Endpoint: `GET /google/oauth/callback`.
- Production redirect URI: `https://api.zumbot.ru/google/oauth/callback`.
- Callback сохраняет OAuth-статус и токены в БД (refresh token хранится зашифрованно).

## 2.1 Актуальная схема старта OAuth (Telegram → Web)

OAuth инициируется через обычную web-страницу, а не внутри скрытых iframe/WebApp.

Явный пользовательский flow:
1. Пользователь нажимает кнопку в Telegram (master bot).
2. Бот отправляет ссылку, открывающую `https://zumbot.ru/connect`.
3. Пользователь проходит Google OAuth на обычной web-странице.
4. После успеха выполняется redirect на `https://zumbot.ru/success`.
5. Пользователь возвращается в Telegram.

Почему так:
- избегаем скрытых iframe;
- избегаем WebApp OAuth-потока;
- делаем consent и контекст авторизации прозрачными для пользователя.

Транспорт токена в web-connect:
- one-time токен передаётся через URL fragment (`#...`), а не query string;
- фронтенд обменивает токен через `POST /auth/telegram/consume`;
- backend выставляет HttpOnly + Secure cookie сессии;
- сырой токен не должен попадать в логи;
- one-time токен имеет TTL и после consume считается недействительным.

Настройки Google OAuth consent screen / client:
- Authorized domain: `zumbot.ru`;
- Redirect URI: `https://api.zumbot.ru/google/oauth/callback` (или ваш backend-домен с тем же callback path).

## 3. Сценарий `refresh_token missing`

Поведение реализовано следующим образом:
1. Если `refresh_token` отсутствует, но в БД уже есть сохранённый refresh token — подключение остаётся успешным (`status=connected`).
2. Если `refresh_token` отсутствует и сохранённого токена нет — статус переводится в ошибку (`status=error` при существующей записи), специалист получает инструкцию переподключить Google с consent + offline.

Операционное действие для пользователя: переподключить Google из master bot и подтвердить запрашиваемые права.

## 4. Smoke-test календарного доступа

После выбора/создания рабочего календаря выполняется smoke-test:
1. `events.insert` тестового события;
2. `events.delete` этого события;
3. фиксация результата в `specialist_calendar_settings`:
   - `last_smoke_test_at`;
   - `last_smoke_test_status` (`ok`/`failed`);
   - `last_smoke_test_error` (короткая причина при ошибке).

Критерий готовности onboarding: календарный шаг считается завершённым только при `last_smoke_test_status=ok`.

## 5. Типовые проблемы

### `insufficientPermissions`
Симптомы:
- OAuth формально завершён, но операции с календарём падают с ошибкой прав.

Что делать:
- повторно инициировать OAuth через master bot;
- убедиться, что пользователь выдал права: просмотр календарей и управление событиями.

### `refresh_token missing`
Симптомы:
- callback сообщает о необходимости переподключения.

Что делать:
- выполнить re-consent с offline-доступом;
- проверить корректность OAuth-конфига в Google Cloud Console.

## 6. Planned/TODO
- Расширенная диагностика и UX для выбора существующего календаря находится в стадии planned.


## OAuth state lifecycle (фиксированный)
- `state` генерируется backend и сохраняется в `oauth_state` c TTL.
- Callback валидирует `state` (существует, не истёк, корректный тип).
- После успешной проверки `state` удаляется (one-time consume).
- Reuse/expired `state` отклоняется.
- `state` не равен `specialist_id`.
