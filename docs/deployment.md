# Развёртывание и запуск Zumbot (обновление конфигурации)

Документ описывает изменения в деплое и запуске backend после перехода на
**systemd socket activation** и обновления nginx-конфигурации для безостановочных
перезапусков. Ниже зафиксированы все правки, их причины и примеры команд для
проверки.

---


## Актуальный runbook для production (VPS)

> Этот раздел фиксирует фактическое окружение на VPS и является основным для релизных действий.

### Что где выполняется
- `[VPS]` — все команды деплоя и эксплуатации (`systemctl`, `journalctl`, `psql`, `curl` в production).
- `[Локально]` — только разработка, проверка и подготовка изменений.
- Git-команды в production выполнять **только от пользователя `zumbot`**.

### Зафиксированные production-параметры
- Путь репозитория на VPS: `/opt/zumbot/backend`.
- Владелец репозитория: `zumbot:zumbot`.
- systemd units:
  - `zumbot-backend.socket` (`ListenStream=127.0.0.1:8000`)
  - `zumbot-backend.service`
- Env-файл: `/etc/zumbot/backend.env` с ключевыми значениями:
  - `APP_ENV=prod`
  - `ENABLE_READYZ=true`
  - `BASE_URL=https://api.zumbot.ru`
  - `PUBLIC_SITE_URL=https://zumbot.ru`
  - `GOOGLE_REDIRECT_URI=https://api.zumbot.ru/google/oauth/callback`
- Продуктивные домены:
  - API: `https://api.zumbot.ru`
  - Site: `https://zumbot.ru`

### Разовые шаги (one-time)
1. Подготовить VPS и каталог `/opt/zumbot/backend` с владельцем `zumbot:zumbot`.
2. Создать `/etc/zumbot/backend.env`.
3. Настроить и включить `zumbot-backend.socket` и `zumbot-backend.service`.
4. Выполнить базовую инициализацию БД и начальные SQL-миграции из `scripts/migrations/*.sql`.

### Шаги на каждый релиз
```bash
[VPS] sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git pull --ff-only'
[VPS] sudo systemctl restart zumbot-backend.service
[VPS] curl -fsS https://api.zumbot.ru/healthz
[VPS] curl -fsS https://api.zumbot.ru/readyz
[VPS] sudo journalctl -u zumbot-backend.service -n 200 --no-pager
```

Ожидаемые ответы:
- `/healthz` -> `200 {"status":"ok","service":"backend"}`
- `/readyz` -> `200 {"status":"ready","db":"ok","loop":"ok"}`
- `/health` и `/ready` не используются в production и возвращают `404`.

### SQL-миграции в релизе
- Каталог миграций: `scripts/migrations/*.sql`.
- Пример применения:
```bash
[VPS] sudo -u postgres bash -lc 'cd /tmp && psql -d zumbot -f /opt/zumbot/backend/scripts/migrations/20260210_add_specialist_calendar_settings.sql'
```
- После миграции обязательно проверить ожидаемые таблицы/индексы (через `to_regclass(...)` и/или `\d`).

### Rollback
```bash
[VPS] sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git log --oneline -n 20'
[VPS] sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git reset --hard <commit_sha>'
[VPS] sudo systemctl restart zumbot-backend.service
[VPS] curl -fsS https://api.zumbot.ru/healthz
[VPS] curl -fsS https://api.zumbot.ru/readyz
```

---

## 1. Изменения в FastAPI backend (код)

### 1.1. Какие файлы/строки менялись

- **`main.py`** — обновлён запуск Uvicorn для поддержки systemd socket activation
  (логика выбора между `fd=3` и обычным `host/port`).

### 1.2. Как добавлена поддержка systemd socket activation

1) Перед запуском Uvicorn код читает переменные окружения, выставляемые systemd:
   - `LISTEN_FDS` — количество переданных file descriptor;
   - `LISTEN_PID` — PID процесса, которому эти дескрипторы принадлежат.

2) Если `LISTEN_FDS=1` и `LISTEN_PID` совпадает с PID текущего процесса, то
   Uvicorn запускается на **`fd=3`**:

```python
listen_fds = os.getenv("LISTEN_FDS")
listen_pid = os.getenv("LISTEN_PID")
use_fd3 = (listen_fds == "1" and listen_pid and int(listen_pid) == os.getpid())

if use_fd3:
    server_config = uvicorn.Config(app=fastapi_app, fd=3, log_level="info")
```

3) При использовании socket activation приложение **не открывает** TCP-порт
   самостоятельно — systemd уже слушает `127.0.0.1:8000` и передаёт сокет
   процессу.

### 1.3. Fallback-поведение (когда socket activation недоступна)

Если `LISTEN_FDS`/`LISTEN_PID` не выставлены или не совпадают, то запускается
стандартный режим:

```python
server_config = uvicorn.Config(
    app=fastapi_app,
    host=config.WEB_HOST,
    port=config.WEB_PORT,
    log_level="info",
)
```

Это обеспечивает **полную обратную совместимость**: локально или в окружениях
без systemd сервис продолжает слушать `WEB_HOST:WEB_PORT`.

---

## 2. Изменения в systemd конфигурации

### 2.1. Новый unit `zumbot-backend.socket`

**Назначение:** держит открытым TCP-сокет `127.0.0.1:8000` и позволяет
безостановочно перезапускать backend без разрыва соединений на стороне nginx.

Пример:

```ini
# /etc/systemd/system/zumbot-backend.socket
[Unit]
Description=Zumbot Backend Socket

[Socket]
ListenStream=127.0.0.1:8000
NoDelay=true
ReusePort=false

[Install]
WantedBy=sockets.target
```

**Почему важно:** systemd начинает принимать соединения ещё до старта сервиса и
передаёт их backend через `fd=3`.

### 2.2. `zumbot-backend.service` и drop-in `socket-activation.conf`

Основной unit запускает приложение (например `python main.py`).
Drop-in-конфигурация добавляет зависимость от socket:

```ini
# /etc/systemd/system/zumbot-backend.service.d/socket-activation.conf
[Unit]
Requires=zumbot-backend.socket
After=zumbot-backend.socket

[Service]
Environment=APP_ENV=prod
```

Это гарантирует, что service стартует только после сокета, и получает от systemd
готовый `fd=3`.

### 2.3. Drop-in `ready-wait.conf`

Для корректного старта nginx/мониторинга добавляется ожидание readiness:

```ini
# /etc/systemd/system/zumbot-backend.service.d/ready-wait.conf
[Service]
ExecStartPost=/usr/bin/bash -c 'for i in {1..30}; do curl -fsS http://127.0.0.1:8000/readyz && exit 0; sleep 1; done; exit 1'
```

Таким образом **systemd считает сервис запущенным только после ответа `/readyz`**.

### 2.4. Почему нужно убрать `PartOf=` у socket unit

Если у socket unit стоит `PartOf=zumbot-backend.service`, то **restart сервиса
может остановить сокет**, и соединения в этот момент будут отклоняться.

Удаление `PartOf=` позволяет сокету:
- жить независимо от service;
- **не падать** во время `systemctl restart zumbot-backend`;
- принимать новые подключения и отдавать их новому процессу.

### 2.5. Как взаимодействуют socket и service

1) `zumbot-backend.socket` слушает `127.0.0.1:8000` постоянно.
2) При старте/рестарте `zumbot-backend.service` systemd передаёт сокет через
   `LISTEN_FDS`/`LISTEN_PID`.
3) Uvicorn принимает fd=3 и сразу начинает обслуживать запросы.
4) Во время рестарта socket остаётся активным → nginx не получает ошибки.

---

## 3. Изменения в nginx конфигурации

### 3.1. Upstream из двух одинаковых серверов

Для повторных попыток (retry) указаны **два одинаковых backend** в upstream:

```nginx
upstream zumbot_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=2s;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=2s;
}
```

Nginx считает их разными целями и может **повторно проксировать запрос** при
ошибке.

### 3.2. Локации `/readyz` и `/healthz`

```nginx
location = /healthz {
    limit_except GET { deny all; }
    proxy_pass http://zumbot_backend;
}

location = /readyz {
    limit_except GET { deny all; }
    proxy_pass http://zumbot_backend;
    proxy_next_upstream error timeout http_502 http_503 http_504;
}
```

- Разрешён только `GET`.
- `/readyz` получает retry-поведение для статусов 5xx и таймаутов.

### 3.3. Retry и таймауты

```nginx
proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_connect_timeout 1s;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 2s;
```

Это даёт второй шанс запросу при коротком «проседании» backend на рестарте.

### 3.4. Пользовательский `error_page` (503)

```nginx
error_page 502 503 504 = /backend-down.json;

location = /backend-down.json {
    internal;
    default_type application/json;
    return 503 '{"status":"down"}';
}
```

Если backend недоступен, nginx возвращает **валидный JSON**:
`{"status":"down"}`.

### 3.5. Поведение nginx при рестарте backend

- socket activation удерживает порт и не даёт ошибку connect.
- nginx делает retry на следующий upstream, поэтому запросы продолжают идти.
- В результате внешний клиент **не видит 503** во время `systemctl restart`.

---

## 4. Тестирование и верификация

### 4.1. Проверка, что при `restart` API продолжает отвечать 200

```bash
# Запустить непрерывный поток запросов
while true; do curl -s -o /dev/null -w "%{http_code}\n" https://api.zumbot.ru/healthz; done

# В другом терминале
sudo systemctl restart zumbot-backend
```

Ожидаем: **все ответы 200**, без 503/502.

### 4.2. Проверка `/readyz` и `/docs`

```bash
curl -i https://api.zumbot.ru/readyz
curl -i https://api.zumbot.ru/docs
```

`/readyz` должен вернуть 200, `/docs` — Swagger UI.

### 4.3. Проверка отсутствия 503 при стресс-тесте (120 запросов)

```bash
for i in {1..120}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.zumbot.ru/healthz; done | sort | uniq -c
```

Ожидаем: **только 200**, без 503/502.

---

## 5. Инструкции по изменению Git репозитория

### 5.1. Как добавить `.venv` в `.gitignore`

```bash
echo ".venv/" >> .gitignore
```

### 5.2. Коммит изменений backend кода

```bash
git add main.py
git commit -m "Add systemd socket activation support"
```

### 5.3. Push на GitHub и локальный pull

```bash
git push origin <branch>

git pull origin <branch>
```

---

## 6. Логи и выгрузки (операционные задачи)

### Переменные окружения
- `DB_URL` — источник БД.
- `ENCRYPTION_KEY` — ключ шифрования (секрет).
- `ADMIN_API_KEY` (опционально) — включает закрытый admin API `/admin/*`.

### Snapshot/backup логов (SQLite/PostgreSQL)
Используйте `scripts/db_snapshot.sh`. Пароли не хранятся в скрипте —
используйте `PGHOST/PGUSER/PGPASSWORD/PGDATABASE` или `.pgpass`.

```bash
# SQLite
DB_URL=sqlite+aiosqlite:///./mvp.db scripts/db_snapshot.sh --out /tmp/zumbot_snapshot.db

# PostgreSQL (последние 7 дней)
DB_URL=postgresql+asyncpg://user@localhost:5432/zumbot \
  PGHOST=127.0.0.1 PGUSER=readonly PGDATABASE=zumbot \
  scripts/db_snapshot.sh --days 7 --out /tmp/zumbot_logs_dump.sql
```

### Безопасное скачивание на локальную машину
```bash
scp user@vps-host:/tmp/zumbot_snapshot.db ./zumbot_snapshot.db
scp user@vps-host:/tmp/zumbot_logs_dump.sql ./zumbot_logs_dump.sql
```

### Опционально: read-only роль для логов (PostgreSQL)
Рекомендуется завести роль только с `SELECT` на таблицы логов:
`message_logs`, `service_heartbeats`, `bot_health_checks`.

---

## 7. Резюме

- Backend теперь поддерживает systemd socket activation (fd=3) и fallback на
  `WEB_HOST:WEB_PORT`.
- systemd socket unit удерживает порт во время рестарта.
- nginx настроен на retry и отдаёт JSON-ошибку при полном падении backend.
- Проверки `/readyz` гарантируют корректную готовность сервиса.

## Shutdown / graceful stop

При корректной остановке backend (например, `systemctl stop/restart`) приложение
закрывает HTTP-сессии Telegram-ботов в следующем порядке:

1. personal bot cache (все кэшированные сессии персональных ботов);
2. master bot session.

Это нужно для устойчивости при деплоях и рестартах: соединения завершаются
предсказуемо, без «висящих» клиентских сессий и лишних ошибок транспорта.
