# Deployment Readiness Guide (MVP)

Документ описывает минимально достаточную процедуру запуска backend в production и первичной операционной проверки.

## A) Требования окружения

### Платформа
- Python 3.11+.
- Linux (рекомендуется Ubuntu 22.04+).
- Доступ к PostgreSQL (production) или SQLite (только local/dev).

### Сеть и порты
- Внешний HTTPS endpoint backend (пример: `https://api.example.com`).
- Порт приложения: `WEB_PORT` (по умолчанию `8000`).
- Входящий HTTPS должен быть доступен для:
  - Telegram webhook запросов;
  - Google OAuth callback.

### Внешние зависимости
- Telegram Bot API (master bot и personal bots).
- Google OAuth 2.0 + Google Calendar API.
- База данных (`DB_URL`): PostgreSQL в production.

## B) Переменные окружения

Ниже перечислены переменные, которые реально читает приложение. Для production обязательность определяется логикой `config.py`.

| Переменная | Назначение | Пример (без секретов) | Критичность | Где используется |
|---|---|---|---|---|
| `APP_ENV` | Режим окружения (`prod`/`local`) | `prod` | optional (автоопределение) | `config.py` |
| `ENABLE_READYZ` | Включение readiness endpoint | `true` | optional | `config.py`, `web_server.py` |
| `MASTER_BOT_TOKEN` | Токен master bot (polling и уведомления) | `123456:***` | required (prod) | `config.py`, `main.py`, `web_server.py` |
| `DB_URL` (`DATABASE_URL` в коде) | Строка подключения к БД | `postgresql+asyncpg://user:***@db:5432/m_bot` | required (prod) | `config.py`, `database.py` |
| `GOOGLE_CLIENT_ID` (`GOOGLE_OAUTH_CLIENT_ID`) | OAuth client id Google | `1234567890-abc.apps.googleusercontent.com` | required (prod) | `config.py`, `services/google_oauth.py` |
| `GOOGLE_CLIENT_SECRET` (`GOOGLE_OAUTH_CLIENT_SECRET`) | OAuth client secret Google | `GOCSPX-***` | required (prod) | `config.py`, `services/google_oauth.py` |
| `GOOGLE_REDIRECT_URI` (`GOOGLE_OAUTH_REDIRECT_URI`) | Redirect URI OAuth callback | `https://api.example.com/google/oauth/callback` | required (prod) | `config.py`, `services/google_oauth.py` |
| `ENCRYPTION_KEY` (`SECRET_KEY`) | Ключ шифрования токенов | `base64-or-hex-key` | required (prod) | `config.py`, `services/crypto.py` |
| `BASE_URL` (`BACKEND_BASE_URL`) | Публичный URL backend для webhook/OAuth ссылок | `https://api.example.com` | required (prod) | `config.py`, Telegram/Google сервисы |
| `PUBLIC_SITE_URL` | Публичный URL сайта/лендинга | `https://example.com` | required (prod) | `config.py` |
| `WEB_HOST` | Host для uvicorn | `127.0.0.1` | optional | `config.py`, `main.py` |
| `WEB_PORT` | Port для uvicorn | `8000` | optional | `config.py`, `main.py` |
| `SERVICE_NAME` | Имя сервиса для heartbeat | `backend` | optional | `config.py`, `web_server.py` |
| `ADMIN_API_KEY` | Включение закрытого admin API | `strong-random-value` | optional | `config.py`, `web_server.py`, `admin_api.py` |
| `LISTEN_FDS` / `LISTEN_PID` | Systemd socket activation | `1` / `<pid>` | optional | `main.py` |

Примечания:
- В коде используется `DB_URL`; переменная `DATABASE_URL` — это внутреннее имя Python-константы.
- В коде используются `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`; алиасы `GOOGLE_OAUTH_*` допустимы только как операционные синонимы в документации/оркестрации (при необходимости проброса в фактические имена).
- В коде используются `BASE_URL` и `ENCRYPTION_KEY`; названия `BACKEND_BASE_URL` и `SECRET_KEY` допустимы как синонимы только при явном маппинге в `BASE_URL`/`ENCRYPTION_KEY`.

## C) Первичный запуск

1. Подготовить окружение и экспортировать обязательные переменные.
2. Применить SQL-миграции/DDL (в репозитории используется инициализация схемы; отдельного Alembic-пайплайна в MVP нет).
3. Запустить backend:
   ```bash
   python main.py
   ```
4. Проверить liveness/readiness:
   ```bash
   curl -i https://api.example.com/healthz
   curl -i https://api.example.com/readyz
   ```

Примечание: `readyz` доступен, только если `ENABLE_READYZ=true`.

## D) Smoke-checks после деплоя

### 1) `/health` и `/ready`
- В текущей реализации приложения рабочие endpoints: `/healthz` и `/readyz`.
- Ожидаемые ответы:
  - `GET /healthz` → `200` и `{"status":"ok","service":"backend"}`.
  - `GET /readyz` → `200` и `{"status":"ready","db":"ok","loop":"ok"}` либо `503` с `status=not_ready`.
- Если в инфраструктуре используются пути `/health` и `/ready`, они должны быть настроены как proxy-alias на `/healthz` и `/readyz` (planned/TODO для унификации).

### 2) Master bot: `/start` → онбординг
1. Открыть master bot.
2. Выполнить `/start`.
3. Проверить, что начался onboarding и создался/обновился профиль специалиста.

### 3) Ввод personal bot token → проверка webhook
1. Ввести token personal bot в master bot.
2. Убедиться по логам, что `getMe` успешен и `setWebhook` выполнен.
3. Проверить в БД активную запись `telegram_bot` с `webhook_url` формата `/tg/webhook/{bot_id}/{secret}`.

### 4) Google OAuth → callback
1. Пройти OAuth-авторизацию из master bot.
2. Убедиться, что callback `GET /google/oauth/callback` завершился без ошибки.
3. Проверить, что `google_oauth.status=connected` и сохранены scope/refresh token (в зашифрованном виде).

### 5) Создание календаря → smoke-test event
1. В master bot выбрать создание календаря.
2. Убедиться, что календарь создан/выбран и сохранён в `specialist_calendar_settings`.
3. Проверить результат smoke-test (`last_smoke_test_status=ok`).

### 6) Переход в personal bot → `/start`, `/status`
1. Открыть personal bot по deep-link.
2. Выполнить `/start` и `/status`.
3. Убедиться, что bot отвечает и показывает актуальный статус интеграций.

## E) Типовые проблемы и диагностика (runbook-lite)

### 1. `401/404` на `/tg/webhook/{bot_id}/{secret}`
**Симптомы:** personal bot не отвечает, в webhook доставке Telegram ошибки.  
**Что проверить:**
- `bot_id` и `secret` в URL совпадают с активной записью в `telegram_bot`;
- `telegram_bot.status = active`;
- публичный HTTPS endpoint доступен извне.

**Где смотреть логи:**
- process logs (`journalctl -u <service>` или контейнерные логи);
- сообщения `Webhook auth failed` / `Webhook payload is not valid JSON`.

**Что сделать:**
- повторно пройти шаг подключения personal bot (ротация webhook secret);
- переустановить webhook через onboarding шаг;
- проверить reverse proxy и TLS chain.

### 2. `insufficientPermissions` в Google OAuth или Calendar API
**Симптомы:** OAuth завершён, но операции с календарём не работают.  
**Что проверить:**
- OAuth scopes включают календарные права;
- consent screen и публикация OAuth app корректны;
- пользователь подтвердил актуальный набор разрешений.

**Где смотреть логи:**
- backend logs по сообщениям `insufficient permissions`;
- таблицы статусов OAuth и smoke-test.

**Что сделать:**
- инициировать переподключение Google (re-consent);
- убедиться, что запрошен offline-доступ и нужные scopes.

### 3. `refresh_token missing`
**Симптомы:** callback выполнен, но постоянный доступ не сохранён.  
**Что проверить:**
- есть ли ранее сохранённый `refresh_token_encrypted` для specialist;
- не был ли OAuth пройден без повторного consent.

**Где смотреть логи:**
- сообщения `OAuth callback missing refresh_token...`;
- запись `google_oauth.status`.

**Что сделать:**
- переподключить Google через onboarding;
- запросить consent/offline access повторно.

### 4. `setWebhook` не ставится
**Симптомы:** onboarding зависает на подключении personal bot, webhook не активен.  
**Что проверить:**
- `BASE_URL` публичный, HTTPS, без приватных адресов;
- endpoint `/tg/webhook/{bot_id}/{secret}` доступен снаружи;
- токен personal bot валиден (`getMe`).

**Где смотреть логи:**
- backend logs по шагам onboarding и Telegram API ошибкам;
- технические проверки `/status` (bot health checks).

**Что сделать:**
- исправить `BASE_URL`;
- устранить сетевые/TLS проблемы;
- переподключить bot token.

### 5. Personal bot не отвечает
**Симптомы:** `/start` в personal bot без ответа.  
**Что проверить:**
- webhook установлен и активен;
- backend запущен и доступен (`/healthz`, `/readyz`);
- specialist имеет статус и связанный active bot.

**Где смотреть логи:**
- webhook ingress логи (`Webhook update accepted`/ошибки обработки);
- `message_logs` и `bot_health_checks`.

**Что сделать:**
- выполнить повторную установку webhook;
- проверить доступность backend и БД;
- перезапустить сервис после исправления конфигурации.

## F) Остановка/рестарт

### Graceful shutdown
При остановке backend должны корректно закрываться:
1. cache personal bot инстансов (`close_personal_bot_cache`);
2. HTTP session master bot (`bot.session.close`).

Это реализовано в lifecycle shutdown (`web_server.py`, `lifespan`) и в завершении polling (`main.py`, `start_bot`).

### Практика перезапуска
1. Выполнить штатный stop через process manager (systemd/docker).
2. Убедиться по логам, что shutdown завершён без исключений закрытия сессий.
3. Выполнить start.
4. Повторить smoke-check минимум по `/healthz`, `/readyz` и webhook.
