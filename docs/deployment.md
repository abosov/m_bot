# Deployment (VPS): пошагово и предсказуемо

Этот документ фиксирует ручной production-деплой в формате «одна команда — один шаг».

## Шаг 1 — забрать изменения из git

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git pull --ff-only'
```

## Шаг 2 — обновить Python-зависимости

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && pip install -r requirements.txt'
```

## Шаг 3 — применить миграции (если есть)

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 "$DB_URL" -f /opt/zumbot/backend/scripts/migrations/20260210_add_specialist_calendar_settings.sql
```

## Шаг 4 — перезапустить systemd unit

```bash
sudo systemctl daemon-reload && sudo systemctl restart zumbot-backend.service
```

## Шаг 5 — проверка /healthz и /readyz изнутри VPS

```bash
curl -fsS http://127.0.0.1:8000/healthz && echo
```

```bash
curl -fsS http://127.0.0.1:8000/readyz && echo
```

## Шаг 6 — проверка /healthz и /readyz снаружи VPS

```bash
curl -fsS https://api.zumbot.ru/healthz && echo
```

```bash
curl -fsS https://api.zumbot.ru/readyz && echo
```

## Шаг 7 — единый человекочитаемый check-report

```bash
sudo bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Ожидается отчёт с `[OK]/[FAIL]` по каждому пункту и `exit code != 0` при любом `FAIL`.

## Шаг 8 — собрать диагностику после деплоя

### 8.1 systemd logs

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

### 8.2 экспорт application-логов

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && python scripts/export_logs.py --source message_logs --limit 500 --redact --out /tmp/message_logs.jsonl'
```

### 8.3 снимок БД (clean, по умолчанию)

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && bash scripts/db_snapshot.sh --out /tmp/zumbot_logs_dump.sql'
```

### 8.4 снимок БД (raw pg_dump)

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && bash scripts/db_snapshot.sh --raw --out /tmp/zumbot_logs_dump_raw.sql'
```

## Planned

- Полностью автоматический deploy pipeline с безопасным rollback и миграциями «в один запуск» (**planned**).
