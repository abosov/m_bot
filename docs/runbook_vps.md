# VPS runbook: ручной деплой без магии

Ниже — предсказуемый сценарий «одна команда = один шаг» для production VPS.

## 0) Предусловия

- Repo: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- systemd units: `zumbot-backend.service`, `zumbot-backend.socket`

## 1) git pull

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git pull --ff-only'
```

## 2) установка зависимостей

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && pip install -r requirements.txt'
```

## 3) миграции (если есть)

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 "$DB_URL" -f /opt/zumbot/backend/scripts/migrations/20260210_add_specialist_calendar_settings.sql
```

> Если миграций несколько: применяйте по одной командой на файл в нужном порядке.

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

## 7) обязательный deploy-check отчёт

```bash
sudo bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Скрипт печатает `[OK]/[FAIL]` по пунктам: `git clean`, `venv exists`, `pip deps installed`, `env vars present`, `postgres reachable`, `/healthz`, `/readyz`, `nginx -t`, `socket activation`.

## 8) сбор диагностики и логов

### 8.1 journalctl

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

### 8.2 export_logs

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && python scripts/export_logs.py --source message_logs --limit 500 --redact --out /tmp/message_logs.jsonl'
```

### 8.3 db_snapshot clean (по умолчанию)

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && bash scripts/db_snapshot.sh --out /tmp/zumbot_logs_dump.sql'
```

### 8.4 db_snapshot raw (при необходимости)

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && bash scripts/db_snapshot.sh --raw --out /tmp/zumbot_logs_dump_raw.sql'
```

## Planned

- Автоматический идемпотентный migration-runner для применения *всех* SQL миграций без ручного списка файлов (**planned**).
