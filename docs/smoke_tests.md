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
4. Создать personal bot и дождаться настройки webhook.
5. Подключить Google OAuth.
6. Выбрать или создать календарь.
7. Запустить smoke-тест календаря.
8. Получить deep-link `?start=owner_panel` в personal bot.

Ожидание: после успешного smoke-теста `specialist.status=active`, выдан deep-link в personal bot.

## 3.3 Personal bot (роль: specialist)

Под `SpecialistOwner` в personal bot:

1. Открыть deep-link `?start=owner_panel` (или `/start` owner).
2. Пройти wizard базовых настроек и сохранить дефолты (интервалы `09:00–12:00` / `13:00–17:00` / `17:00–21:00`, длительность 60, буфер 10, `slot_step_min=15`, `max_sessions_per_day=4`).
3. `/status` — видно:
   - статус подключения Google,
   - поля календаря,
   - информацию о последнем smoke-тесте (если есть).
4. `/help` — приходит справка.

## 3.4 Personal bot (роль: client)

Под `Client` в том же personal bot:

1. `/start` — приходит клиентский stub-ответ.
2. `/help` — приходит stub/справка.

Ожидание: ошибок нет, бот не «молчит» и не падает.

Доп. проверка booking policy: попробуйте `/book_stub` на дату не "завтра" или после cutoff 21:00 по TZ специалиста — должен прийти понятный отказ; после 21:00 по TZ specialist слоты на следующий день не должны выдаваться.

Доп. проверка слотов: убедиться, что применяется `slot_step_min` (только `{60,30,15,10}`, дефолт 15), буфер используется только в вычислении, склейка стык-в-стык интервалов применяется только в domain-валидации слота (в UI интервалы остаются в исходном виде), и действует `max_sessions_per_day` (дефолт 4).

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
