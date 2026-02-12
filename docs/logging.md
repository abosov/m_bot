# Система логирования взаимодействий (Logging System) — v2.0

## Обзор
Система фиксирует все события в экосистеме. Версия 2.0 ориентирована на "читаемость глазами" и глубокую отладку через FSM-состояния.

## Технические логи vs бизнес-логи
**Технические логи** — это наблюдаемость сервиса: доступность, здоровье БД, статус
loop и т.п. Источники: `service_heartbeats`, `bot_health_checks`.

**Бизнес-логи** — история диалога (вход/выход), FSM-состояния и обработчики.
Источник: `message_logs`.

## Что логируется (в MVP)
- входящие и исходящие сообщения Telegram (таблица `message_logs`);
- технические проверки доступности сервиса:
  - `/readyz` → `service_heartbeats` (готовность сервиса);
  - команда `/status` в master_bot → `bot_health_checks` (здоровье личных ботов);
- события best-effort welcome после завершения онбординга:
  - логируется операционный контекст (`specialist_id`, `bot_user_id`/`bot_username`),
    без токенов/секретов.

`/readyz` пишет **ServiceHeartbeat** в `service_heartbeats` — это основной источник
истории доступности сервиса.

`/readyz` по умолчанию включён только в `prod` на VPS.
В `local` он выключен, если явно не задано `ENABLE_READYZ=true`.

## Что запрещено логировать
В логах и технических таблицах **нельзя** хранить секреты и токены:
- `MASTER_BOT_TOKEN`, `bot_token`;
- `refresh_token`, `access_token`;
- `webhook_secret`;
- `oauth` `code`/`state` (кроме безопасного внутреннего идентификатора).

Если нужно указать причину ошибки — пишется краткий тип/код ошибки
без деталей, содержащих секреты.

### Обязательное правило для webhook URL
- Для запросов на `POST /tg/webhook/{bot_id}/{secret}` **запрещено** писать в access-лог
  полный URI (`$request_uri`/`$uri?$args`), так как путь содержит `webhook_secret`.
- Для webhook-маршрута используйте либо:
  1) отключение access-лога, либо
  2) отдельный `log_format` с маскированным путём.

Рекомендуемый вариант для MVP — отдельный формат с маской и явным `map`.

Пример `nginx` (проверяемый):
```nginx
# 1) Выделяем webhook path и скрываем secret в 4-м сегменте пути
map $uri $sanitized_path {
    default $uri;
    ~^/tg/webhook/([0-9]+)/[^/]+$ /tg/webhook/$1/***;
}

# 2) Отмечаем, что это webhook endpoint
map $uri $is_webhook_route {
    default 0;
    ~^/tg/webhook/[0-9]+/[^/]+$ 1;
}

# 2.1) Флаги для условного access_log
map $is_webhook_route $log_webhook_only {
    default 0;
    1 1;
}
map $is_webhook_route $log_non_webhook_only {
    default 1;
    1 0;
}

# 3) Форматы логов: общий и webhook-safe
log_format api_main
    '$remote_addr - $remote_user [$time_local] '
    '"$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';

log_format api_webhook_safe
    '$remote_addr - $remote_user [$time_local] '
    '"$request_method $sanitized_path $server_protocol" '
    '$status $body_bytes_sent "$http_referer" "$http_user_agent"';

server {
    listen 443 ssl;
    server_name api.example.com;

    # Для не-webhook маршрутов можно оставлять обычный формат.
    access_log /var/log/nginx/api_access.log api_main if=$log_non_webhook_only;

    # Для webhook маршрута используем отдельный формат с маскированным путём.
    access_log /var/log/nginx/api_webhook_access.log api_webhook_safe if=$log_webhook_only;

    location /tg/webhook/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Практический чек-лист настройки:
1. В `log_format` не использовать `$request_uri` для webhook-трафика.
2. Маскировать 4-й сегмент пути (`{secret}`) через `map`.
3. Не логировать query string для webhook endpoint.
4. Проверить конфиг: `nginx -t`, затем `systemctl reload nginx`.
5. Выполнить тестовый запрос на `/tg/webhook/<bot_id>/<secret>` и убедиться,
   что в access-логе виден только `/tg/webhook/<bot_id>/***`.

## Операционные инструменты для логов (MVP+)

### Export (JSONL/CSV)
Скрипт `scripts/export_logs.py` выгружает данные в формат, удобный для анализа и
нейросети (JSONL). Для `message_logs` доступен CSV.

Поддерживаемые источники:
- `message_logs`
- `service_heartbeats`
- `bot_health_checks`

Выгрузка всегда сортируется по времени (возрастание).

Примеры:
```bash
# JSONL бизнес-логов за период
python scripts/export_logs.py \
  --source message_logs \
  --since 2024-01-01T00:00:00Z \
  --until 2024-01-02T00:00:00Z \
  --bot-id 123456 \
  --specialist-id 00000000-0000-0000-0000-000000000000 \
  --out /tmp/message_logs.jsonl

# CSV выгрузка message_logs
python scripts/export_logs.py \
  --source message_logs \
  --format csv \
  --out /tmp/message_logs.csv

# Технические логи (heartbeats)
python scripts/export_logs.py \
  --source service_heartbeats \
  --since 2024-01-01T00:00:00Z \
  --limit 1000 \
  --out /tmp/heartbeats.jsonl

# Режим редактирования потенциальных ПДн
python scripts/export_logs.py \
  --source message_logs \
  --redact \
  --limit 500 \
  --out /tmp/message_logs_redacted.jsonl
```

### Runtime logs
По умолчанию runtime-логи backend пишутся в stdout/stderr процесса и доступны через
`journalctl` (если backend запущен под systemd).

- Базовый источник:
  - `journalctl -u zumbot-backend.service --since "24 hours ago" --no-pager`
- Если в окружении задан `LOG_DIR` и директория существует, runtime-логи пишутся
  в файлы (типовая структура):
  - `app.log` — общий лог приложения;
  - `http.log` — HTTP/access контекст;
  - `bot.log` — события Telegram-ботов.

Ротация файлов в `LOG_DIR` настраивается параметрами:
- `maxBytes` — максимальный размер файла до ротации;
- `backupCount` — число архивных файлов (`*.log.*`).

Для упаковки runtime-логов в единый архив используйте:

```bash
scripts/collect_runtime_logs.sh
```

Архив будет создан в `/tmp`:

```text
/tmp/zumbot_logs_bundle_<UTC>.tar.gz
```

Что входит в архив:
- `journalctl_zumbot-backend.log` (за последние 24 часа по умолчанию, либо последние N строк);
- `runtime_logs/*.log` и `runtime_logs/*.log.*` из `LOG_DIR` (если задана и существует);
- `deploy_logs/zumbot_deploy_*.log` и `deploy_logs/zumbot_deploy_check_*.log` (если есть).

Важно: скрипт не читает и не копирует `.env*` файлы и не предназначен для выгрузки секретов.

### Snapshot/backup БД (SQLite/PostgreSQL)
Скрипт `scripts/db_snapshot.sh` делает снапшот только нужных таблиц логов.
Для PostgreSQL используются стандартные переменные окружения `PGHOST/PGUSER/PGPASSWORD/PGDATABASE`
или `.pgpass` (пароли в скрипте не хранятся).

Примеры:
```bash
# SQLite (локально или на VPS с sqlite)
bash scripts/db_snapshot.sh --db-url sqlite+aiosqlite:///./mvp.db --out /tmp/zumbot_snapshot.db

# PostgreSQL (только последние 7 дней)
bash scripts/db_snapshot.sh --days 7 --out /tmp/zumbot_logs_dump.sql

# или прямой URL (переопределяет DB_URL)
bash scripts/db_snapshot.sh --db-url postgresql+asyncpg://user@localhost:5432/zumbot --days 7 --out /tmp/zumbot_logs_dump.sql
```

## Закрытый admin API (опционально)
Если задан `ADMIN_API_KEY`, включаются эндпоинты:
- `GET /admin/logs`
- `GET /admin/heartbeats`
- `GET /admin/bot-health-checks`

**Важно:** не проксировать наружу через nginx; доступ только через SSH tunnel.
Если `ADMIN_API_KEY` не задан —
эндпоинты скрыты и возвращают 404.

Пример SSH tunnel:
```bash
ssh -L 18000:127.0.0.1:8000 user@vps-host
```

Пример запроса:
```bash
curl -H "X-API-Key: <ADMIN_API_KEY>" \
  "http://127.0.0.1:18000/admin/logs?limit=100&since=2024-01-01T00:00:00Z"
```

## Примеры доступа к БД (через SSH tunnel)

### PostgreSQL (psql/DBeaver)
```bash
# Поднимаем туннель до Postgres на VPS
ssh -L 15432:127.0.0.1:5432 user@vps-host

# Далее подключаемся локально (пароль хранится в .pgpass)
psql "host=127.0.0.1 port=15432 dbname=zumbot user=readonly"
```

### SQLite (снапшот + scp + открытие локально)
```bash
# На VPS
bash scripts/db_snapshot.sh --db-url sqlite+aiosqlite:///./mvp.db --out /tmp/zumbot_snapshot.db

# Скачиваем
scp user@vps-host:/tmp/zumbot_snapshot.db ./zumbot_snapshot.db

# Открываем локально (например, sqlite3 или GUI)
sqlite3 ./zumbot_snapshot.db ".tables"
```

## Алгоритм разбора падения/недоступности
1) Проверить мониторинг `/readyz` и последние `service_heartbeats`.
2) Посмотреть `journalctl` и systemd — последние ошибки/рестарты.
3) При `502` — проверить nginx и backend socket/service.
4) При проблемах с БД — проверить DB connectivity и последние heartbeats.
5) Собрать артефакты: `service_heartbeats` + последние 200 строк journalctl.

## Алгоритм разбора бизнес-кейса
1) Найти `bot_id`, `specialist_id` и `tg_user_id`/`appointment_id`.
2) Выгрузить `message_logs` с фильтрами (временной диапазон, IN/OUT).
3) Восстановить диалог по хронологии и сверить `fsm_state`/`handler_name`.
4) При `is_error=true` сопоставить `error_details` с моментом диалога.
5) Подготовить JSONL пакет для нейросети (ограничить период, включить `source` и `timestamp`).

## Приватность и секреты в логах
- Запрещено логировать и выгружать секреты: токены, ключи, OAuth коды, webhook secrets.
- В выгрузках используем только обезличенные идентификаторы
  (`specialist_id`, `client_id`, `appointment_id`, `tg_user_id`).
- При необходимости используйте `--redact` для маскирования email/телефонов
  и блокировки подозрительных токеноподобных строк.
- См. также: `60_security_and_compliance/secrets.md` и
  `60_security_and_compliance/personal_data_policy_notes.md`.

## Схема данных (Table: `message_logs`)

| Группа | Поле | Тип | Описание |
| :--- | :--- | :--- | :--- |
| **IDs** | `id` | UUID | Идентификатор записи лога. |
| **Time** | `created_at` | DateTime | Время события (UTC). |
| **Actors** | `direction` | Enum | `IN` или `OUT`. |
| | `bot_id` | BigInt | ID бота Telegram (`getMe.id`). |
| | `bot_username` | String | Username бота специалиста. |
| | `specialist_name`| String | Публичное имя специалиста. |
| | `user_handle` | String | Никнейм (@username) или имя клиента. |
| **Content**| `message_type` | String | `message`, `callback_query`, `text` и т.д. |
| | `content` | Text | Тело сообщения. |
| **Context**| `fsm_state` | String | Текущий шаг пользователя в боте (FSM State). |
| | `handler_name` | String | Какая функция обработала запрос. |
| **IDs** | `specialist_id` | UUID | Внутренний ID специалиста. |
| | `tg_user_id` | BigInt | ID пользователя в Telegram. |
| **Debug** | `is_error` | Boolean | Была ли ошибка. |
| | `error_details` | Text | Traceback ошибки. |
| | `processing_time`| Float | Время ответа в секундах. |

Примечание:
- Логи хранятся в БД и используются для отладки FSM и бизнес-логики.

## Таблица `service_heartbeats`

Хранит историю технических heartbeat-записей с `/readyz` для диагностики доступности сервиса.
Запись создаётся не чаще одного раза в минуту, чтобы не перегружать БД.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Идентификатор записи. |
| `service_name` | Text | Имя сервиса (например, `backend`). |
| `ts` | DateTime | Время записи (UTC). |
| `db_ok` | Boolean | Статус проверки БД. |
| `loop_ok` | Boolean | Статус проверки event loop. |
| `latency_ms` | Integer | Время ответа `/readyz` в миллисекундах. |
| `details` | Text/JSON | Дополнительные детали (например, ошибка БД). |

## Таблица `bot_health_checks`

Хранит результаты проверок `/status` для personal bot каждого специалиста.
Записи позволяют анализировать периодические ошибки или проблемы с токенами.
В `error_details` допускается только краткая техническая причина без секретов.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Идентификатор записи. |
| `specialist_id` | UUID | Внутренний ID специалиста. |
| `bot_user_id` | BigInt | Telegram ID бота (`getMe.id`). |
| `checked_at` | DateTime | Время проверки (UTC). |
| `status` | Enum | `ok`, `unauthorized`, `temp_error`. |
| `latency_ms` | Integer | Время ответа в миллисекундах. |
| `error_details` | Text | Краткая техническая причина без секретов. |

## Service heartbeat (loop tick)

Помимо логирования сообщений, сервис пишет технические логи health-checks:
- heartbeat_task фиксирует старт/останов фоновой корутины, которая обновляет
  тик event loop каждые 5 секунд. Это позволяет детектировать зависание
  цикла, даже если HTTP-сервер продолжает отвечать.
- `/readyz` логирует `db_ok`, `loop_ok`, `latency_ms` для наблюдаемости
  состояния БД и жизнеспособности event loop.

## Логи shutdown

На graceful shutdown ожидаем технические сообщения (без секретов, токенов и webhook-secret):

- `Personal bot cache closed on shutdown` — personal bot cache закрыт успешно;
- `Failed to close personal bot cache on shutdown` (warning) — ошибка при закрытии cache;
- `Master bot session closed on shutdown` — master bot session закрыта успешно;
- `Failed to close master bot session on shutdown` (warning) — ошибка при закрытии master session.

Эти сообщения помогают быстро проверить корректность lifecycle ресурсов после stop/restart.

## CLI: экспорт логов и DB snapshot

### export_logs.py

```bash
python scripts/export_logs.py --help
python scripts/export_logs.py --source message_logs --since 2026-01-01T00:00:00Z --limit 1000 --format jsonl --out /tmp/message_logs.jsonl
```

### db_snapshot.sh

```bash
bash scripts/db_snapshot.sh --days 3 --out /tmp/zumbot_logs_dump.sql
```

Для PostgreSQL используется plain SQL дамп с флагами `--no-owner --no-privileges --column-inserts --quote-all-identifiers` для большей переносимости между окружениями.
