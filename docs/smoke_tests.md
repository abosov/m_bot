# Smoke-тесты после деплоя

Цель: за **10–15 минут** проверить, что ключевые пользовательские и технические сценарии живы после выката.

## 1) Preconditions (перед запуском)

Перед началом убедитесь, что выполнено:

1. Приложение запущено, база данных доступна.
2. В окружении сервиса задан `ADMIN_API_KEY` (иначе `/admin/*` недоступны).
3. Подготовлены два Telegram-аккаунта:
   - `SpecialistOwner` (владелец специалиста)
   - `Client` (обычный клиент)
4. Специалист уже прошёл онбординг и создал/подключил personal bot.
5. Подключён Google OAuth и выбран календарь.
6. Важно: пользовательский booking flow из **US-03** пока не реализован — клиентская ветка в personal bot сейчас stub и должна корректно отвечать без падения.

---

## 2) Быстрый semi-automated прогон (health + admin)

Скрипт: `scripts/smoke_run.py`

### 2.1. Минимальный запуск

```bash
export BASE_URL="https://<your-host>"
export ADMIN_API_KEY="<admin-api-key>"
python scripts/smoke_run.py
```

Ожидание:
- `GET /healthz` — `200` и `{"status":"ok", ...}`
- `GET /readyz`:
  - если включён (`ENABLE_READYZ=true`) — `200` и `{"status":"ready", ...}`
  - если выключен — допустим `404` (скрипт помечает как OK с комментарием)
- `GET /admin/heartbeats`, `/admin/logs`, `/admin/bot-health-checks` — `200`, корректный JSON с полем `items`.

### 2.2. Проверка свежести логов/heartbeat

```bash
python scripts/smoke_run.py --since-minutes 30
```

Если указан `--since-minutes`, скрипт дополнительно требует, чтобы по каждому admin-эндпоинту были свежие записи за последние N минут.

---

## 3) Manual smoke-сценарии (пошагово, copy/paste)

## 3.1 Web

### Шаг 1: `/healthz`
```bash
curl -sS "$BASE_URL/healthz"
```
Ожидание: JSON содержит `"status":"ok"`.

### Шаг 2: `/readyz`
```bash
curl -i -sS "$BASE_URL/readyz"
```
Ожидание:
- при включённом `ENABLE_READYZ`: `HTTP 200` и `"status":"ready"`
- при выключенном `ENABLE_READYZ`: ожидаемое поведение — `HTTP 404`.

## 3.2 Master bot onboarding (US-01)

Под аккаунтом `SpecialistOwner`:

1. Отправить `/start` в master bot.
2. Пройти создание специалиста.
3. Указать публичное имя.
4. Указать timezone.
5. Создать personal bot и дождаться настройки webhook.
6. Подключить Google OAuth.
7. Выбрать календарь.
8. Запустить smoke-тест календаря (если реализован в текущей версии).

Ожидание: шаги проходят без ошибок, бот даёт понятные статусы, webhook активен.

## 3.3 Personal bot (роль: specialist)

Под `SpecialistOwner` в personal bot:

1. `/start` — показывается панель специалиста.
2. `/status` — видно:
   - статус подключения Google,
   - поля календаря,
   - информацию о последнем smoke-тесте (если есть).
3. `/help` — приходит справка.

## 3.4 Personal bot (роль: client)

Под `Client` в том же personal bot:

1. `/start` — приходит клиентский stub-ответ.
2. `/help` — приходит stub/справка.

Ожидание: ошибок нет, бот не «молчит» и не падает.

## 3.5 Admin

### Heartbeats
1. Вызвать `/readyz` несколько раз (с паузами, с учётом троттлинга записи heartbeat).
2. Проверить `admin/heartbeats`:

```bash
curl -sS -H "X-API-Key: $ADMIN_API_KEY" \
  "$BASE_URL/admin/heartbeats?limit=20"
```

Ожидание: появляются новые записи heartbeat.

### Logs
Проверить логи по тестовому пользователю (`tg_user_id`):

```bash
curl -sS -H "X-API-Key: $ADMIN_API_KEY" \
  "$BASE_URL/admin/logs?tg_user_id=<TEST_TG_USER_ID>&limit=50"
```

Ожидание: есть недавние inbound/outbound записи для тестовых аккаунтов.

---

## 4) Cleanup после прогона

Используйте Phase 1 инструмент сброса тестовых данных:

```bash
python scripts/test_data_reset.py --apply
```

Критично важно:
- **Никогда** не применять reset к реальным аккаунтам.
- Если нужно сохранить других клиентов, регистрируйте и сбрасывайте только выделенные тестовые `tg_user_id`.

Рекомендуемый подход:
1. Завести отдельные Telegram-аккаунты только для smoke.
2. Выполнять reset только по ним.
3. Проверять dry-run перед apply при любых сомнениях.
