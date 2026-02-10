# Google Calendar Integration (MVP)

## OAuth и scopes
Для онбординга требуются scopes, достаточные для:
- создания календаря,
- создания и удаления событий,
- чтения списка календарей.

Используемые scopes:
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

> Если пользователь подключал Google раньше с меньшими правами, нужен re-consent (переподключение через OAuth).

## Требование refresh_token
Для работы интеграции нужен `refresh_token` (offline access), иначе backend не сможет стабильно работать без участия пользователя.

Поведение callback при отсутствии `refresh_token`:
- если в БД уже есть ранее сохранённый refresh_token — используем его, подключение считается успешным (`status=connected`);
- если сохранённого токена нет — подключение помечается как ошибочное (`status=error` при существующей записи), пользователю отправляется инструкция переподключить Google с consent/offline.

---

## Календарный шаг онбординга
После успешного OAuth специалист в master bot должен **явно** выбрать действие:
1. `Создать отдельный календарь (рекомендовано)` — MVP.
2. `Выбрать существующий календарь` — non-MVP UI (архитектура подготовлена, в интерфейсе временная заглушка).

Автовыбор primary-календаря не допускается.

---

## Создание календаря
MVP использует `calendars.insert` с параметрами:
- `summary = "Zumbot - {public_name}"`
- `description = "Calendar created by Zumbot for booking sessions"`
- `timeZone = specialist_profile.specialist_timezone` (или `UTC`)

После создания сохраняются настройки в `specialist_calendar_settings`:
- `calendar_id`
- `calendar_summary`
- `calendar_time_zone`
- `source = created|selected`

---

## Smoke-test доступа (обязательный)
Критерий успешного шага:
- календарь сохранён,
- smoke-test успешно завершён.

Smoke-test:
1. Создать тестовое событие (`events.insert`) на ближайшие ~7 минут, длительность 5 минут.
2. Удалить событие (`events.delete`).
3. Если удаление не удалось — шаг считается проваленным.

Фиксация результата:
- `last_smoke_test_at`
- `last_smoke_test_status` (`ok`/`failed`)
- `last_smoke_test_error` (короткая строка)

---

## Ошибка insufficientPermissions
При `403/insufficientPermissions` пользователь получает сообщение:
- Google подключён,
- но прав недостаточно для создания календаря/событий,
- нужно переподключить аккаунт и выдать все требуемые права.

Технически:
- backend не отдаёт 500 пользователю,
- ошибка обрабатывается и логируется без утечки секретов.

---

## Готовность специалиста
`specialist.status=active` только когда одновременно есть:
- профиль specialist,
- активный personal bot,
- выбранный календарь,
- успешный smoke-test.
