# VPS runbook: ручной деплой без автодеплоя

> Автодеплой из GitHub Actions **не используем**. Прод-деплой выполняется вручную на VPS.

## Базовые пути

- Репозиторий: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- Деплой-скрипт: `/opt/zumbot/backend/scripts/vps_deploy.sh`
- Check-скрипт: `/opt/zumbot/backend/scripts/vps_deploy_check.sh`

## Команды ручного запуска

```bash
# checks
sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh'

# deploy
sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh --mode deploy'
```

`vps_deploy_check.sh` в режиме `checks` делает только валидации без `git pull`/`pip install`/`restart`, но выполняет idempotent-проверку миграций через `scripts/run_migrations.sh` (обёртка над `scripts/db_migrate.sh`, с автозагрузкой `/etc/zumbot/backend.env`).

Отдельным шагом запускается **Encoding guard** (`scripts/check_encoding.py`) для проверки UTF-8 и признаков mojibake в репозитории.

`vps_deploy_check.sh --mode deploy` выполняет ручной деплой и затем пост-проверки:
- `git fetch` + `git pull --ff-only origin main`;
- `pip install -r requirements.txt` в `.venv` от пользователя `zumbot`;
- загрузка env из `/etc/zumbot/backend.env`;
- запуск SQL-миграций (`scripts/run_migrations.sh`);
- `systemctl restart zumbot-backend.service`;
- ожидание `/readyz`;
- запуск пост-проверок.


## Heartbeat throttling и интерпретация health/readiness

`/readyz` может вызываться часто (monitoring, LB, ручные проверки), поэтому запись
в `service_heartbeats` дросселируется переменной `HEARTBEAT_WRITE_INTERVAL_SEC`.

Контракт:
- readiness вычисляется на **каждый** запрос `/readyz` (проверка БД + event loop);
- запись в `service_heartbeats` создаётся не на каждый запрос, а не чаще чем раз в
  `HEARTBEAT_WRITE_INTERVAL_SEC`;
- если запросы приходят чаще интервала, часть запросов не создаёт новую запись в БД;
- это нормальное поведение и не считается потерей readiness-данных.

Когда heartbeat обновляется:
- первый проход после старта сервиса;
- очередной `/readyz`, когда истёк интервал throttling;
- следующий допустимый запрос после окна throttling.

Когда heartbeat **не** обновляется:
- `/readyz` приходит раньше, чем истёк `HEARTBEAT_WRITE_INTERVAL_SEC`;
- нет смены окна записи (обычный режим частых probes).

Влияние на диагностику:
- для текущего статуса используйте HTTP-код/тело `/readyz` и `/healthz`;
- для истории во времени используйте `service_heartbeats`, учитывая, что это
  дискретные точки с дросселированием, а не лог каждого probe-запроса.

Проверка после деплоя:
```bash
# 1) Быстрые вызовы /readyz (например, 5-10 раз подряд)
for i in {1..10}; do curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/readyz; done

# 2) Проверяем, что HTTP 200/503 возвращается корректно,
#    но число новых записей в service_heartbeats меньше числа вызовов.
```


## Базовая защита nginx от сканеров

Минимальный MVP-конфиг лежит в репозитории: `docs/snippets/nginx_security.conf`.

1. Скопируйте сниппет на VPS:

```bash
sudo install -D -m 0644 /opt/zumbot/backend/docs/snippets/nginx_security.conf /etc/nginx/snippets/zumbot_security.conf
```

2. Добавьте `limit_req_zone` из сниппета в контекст `http {}` в `/etc/nginx/nginx.conf` (если ещё не добавлен).

3. Подключите include в нужный `server {}` (backend host, например `api.zumbot.ru`):

```nginx
server {
    listen 443 ssl;
    server_name api.zumbot.ru;

    include /etc/nginx/snippets/zumbot_security.conf;

    # Важно: наружу проксируем только публичные endpoint'ы backend,
    # admin API не публикуем.
}
```

4. Проверьте и примените nginx-конфиг:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

5. Быстрая валидация блокировок/scanner-path:

```bash
curl -I https://api.zumbot.ru/wp-admin
curl -I https://api.zumbot.ru/.env
```

Ожидаемо: соединение может закрываться кодом `444`, либо возвращаться deny-ответ nginx в зависимости от клиента.

## Fail2ban (опционально)

`fail2ban` можно включить поверх nginx-логов как дополнительный слой защиты.

Вариант в репозитории: `scripts/setup_fail2ban.sh` (идемпотентный, без автозапуска).

### Минимальный профиль

- jail `nginx-badbots` (штатный fail2ban);
- кастомный jail `nginx-zumbot-scanners` по scanner-path (`/wp-admin`, `/.env`, `/phpmyadmin`, `/cgi-bin`, `/vendor`, `/actuator` и т.д.).

### Установка и запуск

```bash
# 1) (опционально) установить/обновить fail2ban + положить jail/filter
sudo bash /opt/zumbot/backend/scripts/setup_fail2ban.sh

# 2) проверить статус
sudo fail2ban-client status
sudo fail2ban-client status nginx-zumbot-scanners

# 3) убедиться, что сервис в автозапуске
sudo systemctl is-enabled fail2ban
sudo systemctl status fail2ban --no-pager
```

Если не используете скрипт, минимальная конфигурация вручную:

- `/etc/fail2ban/filter.d/nginx-zumbot-scanners.conf`:

```ini
[Definition]
failregex = ^<HOST> - .*"(?:GET|POST|HEAD|OPTIONS) /(wp-admin|wp-login\.php|\.env|phpmyadmin|cgi-bin|vendor|actuator|\.git|boaform|HNAP1).*" (?:403|404|444) .*$
ignoreregex =
```

- `/etc/fail2ban/jail.d/zumbot-nginx.local`:

```ini
[nginx-zumbot-scanners]
enabled = true
port = http,https
filter = nginx-zumbot-scanners
logpath = /var/log/nginx/access.log
maxretry = 8
findtime = 10m
bantime = 1h

[nginx-badbots]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 3
findtime = 10m
bantime = 1h
```


## Smoke-check после деплоя

P0/MUST: для production запрещён релиз, если `webhook_secret` может попасть в nginx access log.
После `bash scripts/vps_deploy_check.sh --mode deploy` обязательно проверьте, что в логе есть успешные шаги:

- `Smoke: /healthz` → HTTP 200;
- `Smoke: /readyz` → HTTP 200;
- `Smoke: service journal scan` → за последние 5 минут нет `priority=err` и `Traceback`;
- `Smoke: webhook log masking` → в nginx access log есть только маскированный путь `/tg/webhook/<bot_id>/***`, а сырой `/tg/webhook/<bot_id>/<secret>` отсутствует;
- `Smoke: master bot getMe` → `ok=true`;
- опционально `Smoke: test personal bot getMe` (если задан `TEST_PERSONAL_BOT_TOKEN`).
- smoke-check публичного specialist route: `GET /{slug}` содержит актуальный bridge-маркер `const apiBaseUrl = ...`, а `GET /api/public/specialists/{slug}` отвечает 200 для опубликованного slug.

Чеклист руками:

```bash
# 1) полный checks/deploy прогон
sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh --mode deploy'

# 2) health/readiness
curl -fsS --max-time 5 http://127.0.0.1:8000/healthz
curl -fsS --max-time 5 http://127.0.0.1:8000/readyz

# 3) последние ошибки сервиса
sudo journalctl -u zumbot-backend.service --since "5 minutes ago" --no-pager

# 4) webhook log masking (обязательный P0-check, секрет не печатаем)
source /etc/zumbot/backend.env
sudo grep -E '/tg/webhook/[0-9]+/\*\*\*' /var/log/nginx/api_webhook_access.log
if sudo grep -F -- "/tg/webhook/${TEST_PERSONAL_BOT_ID}/${TEST_PERSONAL_WEBHOOK_SECRET}" /var/log/nginx/api_webhook_access.log >/dev/null; then
  echo "[FAIL] raw webhook path detected in nginx access log"
  exit 1
fi

# 5) master-bot getMe (токен из /etc/zumbot/backend.env)
source /etc/zumbot/backend.env
curl -fsS --max-time 8 "https://api.telegram.org/bot${MASTER_BOT_TOKEN}/getMe"

# 6) public specialist bridge + API smoke (для опубликованного slug)
slug="TsarevaE_12"  # замените на реальный опубликованный slug
curl -s "https://zumbot.ru/${slug}" | grep "const apiBaseUrl"
curl -i "https://api.zumbot.ru/api/public/specialists/${slug}"

# 7) observability: route render log
sudo journalctl -u zumbot-backend.service --since "10 minutes ago" --no-pager   | grep "event=public_slug_route_rendered" | tail -n 20
```

Признаки OK:
- `RESULT=OK` в конце лога `/tmp/zumbot_deploy_*.log`;
- `/healthz` и `/readyz` отвечают 200;
- в `journalctl` нет свежих ERROR/Traceback;
- Telegram `getMe` возвращает JSON с `"ok": true`;
- webhook path в nginx логируется только в маскированном виде (`***`), без `webhook_secret`.
- `curl -s https://zumbot.ru/{slug} | grep "const apiBaseUrl"` показывает актуальный bridge-маркер;
- `curl -i https://api.zumbot.ru/api/public/specialists/{slug}` возвращает HTTP 200 для опубликованного slug;
- в `journalctl` есть INFO `event=public_slug_route_rendered ... route_name=specialist_profile_page ...`.


### Smoke-check reminders (test env)

Цель: проверить, что scheduler создаёт reminder outbox event, а delivery проходит через outbox worker.

```sql
-- 1) создайте confirmed appointment со start_at_utc = now() + interval '24 hours'
-- (через тестовые фикстуры/SQL в вашем стенде)

-- 2) дождитесь scheduler-цикла (~1 минута) и проверьте запись reminder
SELECT appointment_id, reminder_type, due_at_utc, sent_at_utc
FROM appointment_reminder
WHERE due_at_utc <= now() + interval '1 minute'
ORDER BY created_at_utc DESC
LIMIT 20;

-- 3) проверьте, что появился outbox event
SELECT id, event_type, processed_at, attempts, error
FROM outbox_events
WHERE event_type IN ('appointment_client_reminder_24h', 'appointment_client_reminder_2h')
ORDER BY created_at DESC
LIMIT 20;
```

Проверка delivery:
- после обработки outbox worker в `appointment_reminder.sent_at_utc` появляется timestamp;
- в message logs текст reminder не должен содержать `appointment_id`/UUID (UUID допускается только в callback_data).

## Где смотреть логи

- Лог запуска: `/tmp/zumbot_deploy_*.log`

- В конце каждого запуска скрипт печатает:
  - `LOG_PATH=/tmp/...`
  - `EXIT_CODE=0|1`
  - `RESULT=OK|FAIL`
- Логи сервиса:

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

## Outbox Operations

- `handler_missing` — событие не обработано, потому что для его типа не найден зарегистрированный обработчик.
- `dead_letter` — событие переведено в «мёртвую очередь» после исчерпания попыток обработки.

Новые reminder/event-типы:
- `appointment_client_reminder_24h` — напоминание клиенту за 24 часа (кнопки confirm/cancel/contact);
- `appointment_client_reminder_2h` — напоминание клиенту за 2 часа (кнопка contact);
- `appointment_client_confirmed` — уведомление специалисту, что клиент подтвердил встречу;
- `appointment_client_contact_specialist` — уведомление специалисту, что клиент просит связаться.

Чтобы найти зависшие события, смотрите записи outbox без `processed_at`.

```sql
SELECT id, event_type, attempts, error
FROM outbox_events
WHERE processed_at IS NULL;
```

Для reminder-событий:

```sql
SELECT id, event_type, attempts, error
FROM outbox_events
WHERE processed_at IS NULL
  AND event_type LIKE 'appointment_client_%';
```

## Troubleshooting

1. Найдите последний лог:  
   `ls -1t /tmp/zumbot_deploy_*.log | head -n 1`
2. Если запуск уже завершён, можно взять `LOG_PATH` из последних строк вывода скрипта.
3. Для диагностики пришлите:

```bash
tail -n 200 <LOG_PATH>
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

3. Диагностика reminder-доставки (зависшие reminders):

```sql
SELECT *
FROM appointment_reminder
WHERE sent_at_utc IS NULL
  AND due_at_utc < now() - interval '10 minutes';
```

4. Диагностика pending outbox reminder-событий:

```sql
SELECT id, event_type, attempts, error
FROM outbox_events
WHERE processed_at IS NULL
  AND event_type LIKE 'appointment_client_%';
```


## Безопасный сброс тестовых данных smoke-аккаунтов

Используйте команду `zumbot-test-reset` (symlink на `scripts/test_data_reset_run.py`).

Реестр выбирается автоматически:
1) `/etc/zumbot/test_accounts.yaml` (prod, права `600`, владелец `zumbot`);
2) fallback `config/test_accounts.yaml`.

`DB_URL` подхватывается автоматически из `/etc/zumbot/backend.env`.

```bash
# dry-run по умолчанию
zumbot-test-reset

# apply только с двойным подтверждением
zumbot-test-reset --apply --i-know-what-i-am-doing --yes
```

Дополнительно:
- выборочные аккаунты: `zumbot-test-reset --names smoke_specialist_1 smoke_client_1`;
- явные `tg_user_id`: `zumbot-test-reset --tg-user-ids 123 456`;
- форс-режим (осознанно): `zumbot-test-reset --apply --i-know-what-i-am-doing --yes --force`.

Скрипт удаляет только связанные данные тестовых аккаунтов и не трогает глобальные heartbeat-записи (`service_heartbeats`).

## Диагностика после онбординга и действий

Цель: собрать полный диагностический пакет в 1 команду на VPS и получить автоматический verdict по US-01 и базовым настройкам (`PASS/WARN/FAIL`).

### 1 команда на VPS (сбор + проверка)

```bash
sudo bash /opt/zumbot/backend/scripts/diag_collect.sh --owner-tg-id 123 --check
```

Скрипт создаёт архив вида `/tmp/zumbot_diag_<UTCSTAMP>.tar.gz`, записывает подробности в `summary.txt` (и `summary.json` при `--json`) и печатает в stdout только:
- путь к архиву,
- `OVERALL: PASS|WARN|FAIL`,
- при `FAIL` — строку `See summary.txt in archive`.

### 1 команда на локальном Mac

```bash
bash scripts/diag_fetch_local.sh root@<host>
```

Скрипт сам найдёт последний архив на VPS, скачает его в `~/Downloads/zumbot_diag/`, распакует и выведет путь + команды для просмотра.

### Диагностика: режим проверки

Новые флаги:
- `--check` — запуск строгой DB-проверки US-01 + базовых настроек,
- `--check-only` — только проверка (без логов и архива),
- `--json` — добавить machine-readable verdict в `summary.json`.

Коды выхода в check-режиме:
- `0` — `PASS`,
- `10` — `WARN`,
- `20` — `FAIL`.

`summary.txt` в check-режиме теперь включает структурированные блоки:
- `FAILURES` — критичные проблемы (ломают готовность US-01),
- `WARNINGS` — некритичные проблемы/ограничения,
- `OVERRIDES (INFO)` — валидные отклонения от дефолтов (это не ошибка),
- `NOTES` — контекст (например, fallback по timezone).

Пример блока `OVERRIDES (INFO)`:

```text
OVERRIDES (INFO):
  - session_duration_min: expected 60, actual 90 (overridden)
  - slot_step_min: expected 15, actual 30 (overridden)
  - weekly_availability: differs from defaults (overridden)
```

Важно: отличия от дефолтов (timezone, длительность сессии, буфер, cancel window, лимиты, weekly availability) считаются `INFO` при валидных значениях и не переводят verdict в `WARN/FAIL`.

В обычном режиме (без `--check`) скрипт по-прежнему завершает работу с `exit 0`.

### Типовые короткие сценарии

После регистрации специалиста (по owner tg id):

```bash
sudo bash /opt/zumbot/backend/scripts/diag_collect.sh --owner-tg-id 123 --check
```

После изменения настроек специалиста (по specialist id):

```bash
sudo bash /opt/zumbot/backend/scripts/diag_collect.sh --specialist-id 456 --check --since "30 minutes ago"
```

Только проверка без архива:

```bash
sudo bash /opt/zumbot/backend/scripts/diag_collect.sh --owner-tg-id 123 --check-only
```

### Локальный запуск Encoding guard

Зачем: чтобы до деплоя находить проблемы кодировки (не-UTF-8 и «кракозябры»/mojibake) и не тащить их в main/prod.

```bash
python scripts/check_encoding.py
```

Строгий режим (warning считается ошибкой):

```bash
python scripts/check_encoding.py --strict-warn
```
