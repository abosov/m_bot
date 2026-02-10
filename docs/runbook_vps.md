# VPS runbook: честный ручной деплой

> Прод-деплой выполняется вручную на VPS, без GitHub Actions.

## Базовые пути

- Репозиторий: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- Скрипт деплоя: `/opt/zumbot/backend/scripts/vps_deploy_check.sh`

## Единственная команда деплоя

```bash
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Скрипт:
- требует запуск от `root` (иначе `exit 1`);
- проверяет окружение;
- применяет SQL-миграции через `psql "$PSQL_URL" -v ON_ERROR_STOP=1 -f <file>`;
- перезапускает сервис;
- проверяет локальные `/healthz` и `/readyz` после рестарта (только HTTP 200 считается успехом);
- в конце всегда печатает:
  - `RESULT=OK|FAIL`
  - `LOG_PATH=/tmp/zumbot_deploy_check_*.log`

## Как читать результат

1. Возьмите `LOG_PATH` из финального вывода.
2. Посмотрите хвост лога:

```bash
tail -n 200 <LOG_PATH>
```

При падении скрипт печатает `FAILED_STEP=<...>`, чтобы было видно, на каком шаге остановка.

## Типовые фейлы и что делать

### 1) `DB_URL invalid`

Признаки в логе:
- `[FAIL] Run SQL migrations - invalid DB_URL format (pgsql dbname is required)`

Причина:
- `DB_URL` не содержит имя базы (нет `/<dbname>`), либо схема не postgres/postgresql.

Проверка:

```bash
sudo sed -n '1,200p' /etc/zumbot/backend.env | rg '^DB_URL='
```

Исправление:
- привести `DB_URL` к корректному виду SQLAlchemy URL с dbname, например:
  - `postgresql+asyncpg://user:pass@host:5432/zumbot`

---

### 2) `psql failed`

Признаки в логе:
- `[FAIL] Run SQL migrations - psql connection self-check failed`
- `[FAIL] Run SQL migrations - migration failed: <file>.sql`
- `[FAIL] Run SQL migrations - failed to record applied migration: <file>.sql`

Причины:
- недоступна БД / неверные креды;
- синтаксическая ошибка миграции;
- ошибка прав на таблицу `applied_migrations`.

Проверка:

```bash
tail -n 200 <LOG_PATH>
```

```bash
sudo journalctl -u zumbot-backend.service -n 200 --no-pager
```

---

### 3) `readyz not OK`

Признаки в логе:
- `[FAIL] /readyz - endpoint is unavailable`

Важно:
- проверка `/healthz` и `/readyz` выполняется **после** `systemctl restart zumbot-backend.service`.
- success только при HTTP 200.

Проверка вручную:

```bash
curl -i --max-time 5 http://127.0.0.1:8000/healthz
curl -i --max-time 5 http://127.0.0.1:8000/readyz
```

Если `/readyz` не 200, проверьте доступность БД и настройки backend env.
