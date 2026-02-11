# Deployment Readiness Guide (MVP)

Документ описывает фактический production-деплой на VPS и операционные проверки после релиза.

## Где выполнять команды

- `[VPS]` — выполнять на production-сервере Zumbot.
- `[Локально]` — выполнять на рабочей машине разработчика.
- Если в примере нет метки, команда приводится только как справка и должна быть адаптирована под контекст.

Принцип: всё, что связано с systemd, nginx, `/etc/zumbot/backend.env`, journalctl, Postgres на `127.0.0.1`, выполняется на VPS.

## Доменная схема production

- Сайт (frontend): `https://zumbot.ru`.
- Backend API: `https://api.zumbot.ru`.
- Google OAuth redirect URI: `https://api.zumbot.ru/google/oauth/callback`.

Эти значения задаются в `/etc/zumbot/backend.env`.

Проверка фактических значений:

```bash
[VPS] sudo sed -n '/^BASE_URL=/p;/^PUBLIC_SITE_URL=/p;/^GOOGLE_REDIRECT_URI=/p' /etc/zumbot/backend.env
```

## A) Требования окружения

### Платформа
- Python 3.11+.
- Linux (рекомендуется Ubuntu 22.04+).
- Доступ к PostgreSQL (production) или SQLite (только local/dev).

### Сеть и порты
- Внешний HTTPS endpoint backend: `https://api.zumbot.ru`.
- Порт backend-процесса на localhost: `127.0.0.1:8000`.
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

1. `[VPS]` Подготовить окружение и убедиться, что обязательные переменные заданы в `/etc/zumbot/backend.env`.
2. `[VPS]` Применить SQL-миграции/DDL (используются SQL-скрипты, Alembic не используется).
   - Для уже существующих БД убедиться, что в `specialist_profile` есть поля `session_duration_min`, `session_buffer_min` и действуют соответствующие CHECK-ограничения (`duration > 0`, `buffer >= 0` по бизнес-правилам MVP).
3. `[VPS]` Запустить backend через systemd (socket activation):
   ```bash
   sudo systemctl restart zumbot-backend.socket zumbot-backend.service
   ```
4. `[VPS]` Проверить liveness/readiness:
   ```bash
   curl -fsS https://api.zumbot.ru/healthz
   curl -fsS https://api.zumbot.ru/readyz
   ```

Примечание: на production `ENABLE_READYZ` должен быть включён.

## D) Systemd socket activation (production)

В production включена socket activation:

- `zumbot-backend.socket` слушает `127.0.0.1:8000`.
- `zumbot-backend.service` запускается systemd при входящем соединении в socket.
- Nginx проксирует `api.zumbot.ru` на `127.0.0.1:8000`.

Операционные команды:

```bash
[VPS] sudo systemctl status zumbot-backend.socket zumbot-backend.service --no-pager
[VPS] sudo systemctl cat zumbot-backend.socket
[VPS] sudo systemctl cat zumbot-backend.service
[VPS] sudo journalctl -u zumbot-backend.service -n 200 --no-pager
[VPS] sudo ss -ltnp | rg '127.0.0.1:8000|:443|:80'
```

Критерии корректной конфигурации:
- socket unit активен и слушает `127.0.0.1:8000`;
- service unit запускается без ошибок;
- Nginx обслуживает оба домена: `zumbot.ru` и `api.zumbot.ru`.

## E) Smoke-checks после деплоя

### Критерии успеха health/readiness

```bash
[VPS] curl -i https://api.zumbot.ru/healthz
[VPS] curl -i https://api.zumbot.ru/readyz
[VPS] curl -i https://api.zumbot.ru/health
[VPS] curl -i https://api.zumbot.ru/ready
[VPS] curl -i https://api.zumbot.ru/
```

Ожидаемый результат:
- `GET /healthz` → `200` и `{"status":"ok","service":"backend"}` — сервис жив.
- `GET /readyz` → `200` и `{"status":"ready","db":"ok","loop":"ok"}` — сервис готов к работе.
- `GET /health` → `404` — путь не используется.
- `GET /ready` → `404` — путь не используется.
- `GET /` → `404` — для backend это ожидаемо.

### 1) Health/readiness
- В production используются только `/healthz` и `/readyz`.
- `/health` и `/ready` считаются неиспользуемыми (возвращают `404`).

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

## F) Что делается разово, а что на каждый релиз

### Разово (первичная подготовка VPS)
- Установка системных пакетов и runtime.
- Настройка `/etc/zumbot/backend.env`.
- Настройка nginx для доменов `zumbot.ru` и `api.zumbot.ru`.
- Выпуск и подключение TLS-сертификатов.
- Создание и включение systemd unit-файлов (`zumbot-backend.socket`, `zumbot-backend.service`).

Проверки после разовой настройки:

```bash
[VPS] sudo nginx -t
[VPS] sudo systemctl enable --now zumbot-backend.socket
[VPS] sudo systemctl status nginx zumbot-backend.socket --no-pager
```

### Каждый релиз
- Обновить код (`git pull`).
- При необходимости применить SQL-миграции.
- Перезапустить backend unit’ы.
- Выполнить smoke-checks (`/healthz`, `/readyz`, onboarding/webhook/OAuth).

Пример минимального релизного цикла:

```bash
[VPS] cd /opt/zumbot/m_bot && git pull --ff-only
[VPS] sudo systemctl restart zumbot-backend.socket zumbot-backend.service
[VPS] curl -fsS https://api.zumbot.ru/healthz
[VPS] curl -fsS https://api.zumbot.ru/readyz
```

## G) Типовые проблемы и диагностика (runbook-lite)

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

## H) Остановка/рестарт

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
