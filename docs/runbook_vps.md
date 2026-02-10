# VPS runbook: ручной деплой без магии

Ниже — предсказуемый сценарий «одна команда = один шаг» для production VPS.

## 0) Предусловия

- Repo: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- systemd units: `zumbot-backend.service`, `zumbot-backend.socket`

Перед миграциями, дампом БД и экспортом логов загрузите переменные окружения:

```bash
set -a && source /etc/zumbot/backend.env && set +a
```

## 1) git pull

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git pull --ff-only'
```

## 2) установка зависимостей

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && pip install -r requirements.txt'
```

## 3) миграции

Рекомендуемый способ — через `scripts/vps_deploy_check.sh`: скрипт сам

- нормализует `DB_URL` в DSN формата `postgresql://...` (поддерживает `postgresql+asyncpg://`, `postgres://`, `postgresql://`);
- проверяет, что в `DB_URL` указан `dbname` (если нет — завершает проверку с `FAIL`);
- делает self-check подключения через `psql` (`SELECT 1`);
- применяет **все** `scripts/migrations/*.sql` в лексикографическом порядке;
- запускает `psql` с `ON_ERROR_STOP=1`, поэтому любая ошибка миграции останавливает деплой с `exit 1`.

> Скрипт не печатает полный DSN/`DB_URL` в логах, чтобы не утекали секреты.

Для ручного запуска (диагностика):

```bash
cd /opt/zumbot/backend
mapfile -t files < <(find scripts/migrations -maxdepth 1 -type f -name '*.sql' | sort)
for f in "${files[@]}"; do
  sudo -u zumbot psql "${DB_URL/postgresql+asyncpg:\/\//postgresql://}" -v ON_ERROR_STOP=1 -f "$f"
done
```

Диагностика ошибок миграций:

1. Проверить, что `DB_URL` задан и содержит имя БД после `/` (например `...:5432/zumbot_db`).
2. Проверить доступность `psql`: `psql --version`.
3. Проверить подключение без запуска миграций:
   `sudo -u zumbot psql "${DB_URL/postgresql+asyncpg:\/\//postgresql://}" -v ON_ERROR_STOP=1 -tAc 'SELECT 1'`.
4. Если шаг `Run SQL migrations` в `vps_deploy_check.sh` вернул `[FAIL]`, смотреть stderr `psql` и исправлять проблемный SQL-файл.

## 4) restart systemd

```bash
sudo systemctl daemon-reload && sudo systemctl restart zumbot-backend.service
```

## 5) проверка изнутри VPS (/healthz, /readyz)

```bash
curl -fsS http://127.0.0.1:8000/healthz && echo
```

```bash
curl -fsS http://127.0.0.1:8000/readyz && echo
```

## 6) проверка снаружи VPS (/healthz, /readyz)

```bash
curl -fsS https://api.zumbot.ru/healthz && echo
```

```bash
curl -fsS https://api.zumbot.ru/readyz && echo
```

## 7) Запуск проверок

```bash
sudo bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Подробный режим (версии, пути, хвост логов):

```bash
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Скрипт печатает `[OK]/[FAIL]` по каждому пункту с короткой причиной и в конце выводит `SUMMARY: OK=<N> FAIL=<M>` + `EXIT_CODE=<0|1>`.

## 8) Экспорт логов и диагностика

### 8.1 journalctl

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

### 8.2 export_logs

Скрипт самодостаточный: можно вызывать из любого каталога без `PYTHONPATH`.

```bash
cd /opt/zumbot/backend
python scripts/export_logs.py --help
python scripts/export_logs.py --source message_logs --limit 500 --redact --out /tmp/message_logs.jsonl
```

### 8.3 db_snapshot clean (по умолчанию)

Скрипт по умолчанию сам подхватывает `DB_URL` из `/etc/zumbot/backend.env`, если `DB_URL` не передан явно.

```bash
cd /opt/zumbot/backend
bash scripts/db_snapshot.sh --out /tmp/zumbot_logs_dump.sql
```

### 8.4 db_snapshot raw (при необходимости)

`--raw` сохраняет оригинальный вывод `pg_dump` (включая `\restrict` / `\unrestrict`). Без `--raw` эти строки автоматически отфильтровываются.

```bash
cd /opt/zumbot/backend
bash scripts/db_snapshot.sh --raw --out /tmp/zumbot_logs_dump_raw.sql
```

