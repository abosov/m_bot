# Google Calendar Integration (MVP)

## 1. OAuth требования

Для onboarding требуется OAuth 2.0 с offline-доступом и календарными scope.

Минимальные scope текущего MVP:
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

Если пользователь уже выдавал доступ с меньшими правами, требуется re-consent (повторное подключение).

## 2. Callback endpoint

- Endpoint: `GET /google/oauth/callback`.
- Production redirect URI: `https://api.zumbot.ru/google/oauth/callback`.
- Callback сохраняет OAuth-статус и токены в БД (refresh token хранится зашифрованно).

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
- убедиться, что пользователь выдал полный набор scope.

### `refresh_token missing`
Симптомы:
- callback сообщает о необходимости переподключения.

Что делать:
- выполнить re-consent с offline-доступом;
- проверить корректность OAuth-конфига в Google Cloud Console.

## 6. Planned/TODO
- Расширенная диагностика и UX для выбора существующего календаря находится в стадии planned.
