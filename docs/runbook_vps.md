# VPS runbook: каноничный ручной деплой

> На данный момент деплой **не встроен в GitHub Actions**. Production-деплой выполняется вручную на VPS.

## Базовые пути

- Репозиторий: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- Проверочный скрипт: `/opt/zumbot/backend/scripts/vps_deploy_check.sh`

## Каноничный процесс деплоя

1. Обновить код:

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && git pull --ff-only'
```

2. Обновить зависимости:

```bash
sudo -u zumbot -H bash -lc 'cd /opt/zumbot/backend && source .venv/bin/activate && pip install -r requirements.txt'
```

3. Перезапустить backend:

```bash
sudo systemctl daemon-reload
sudo systemctl restart zumbot-backend.service
```

4. Запустить единый post-deploy check (включая SQL-миграции):

```bash
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

## Что делает `vps_deploy_check.sh`

- Проверяет git/venv/deps/env/sockets/nginx/health endpoints.
- В блоке `Run SQL migrations`:
  - приводит `DB_URL` к psql-совместимому виду через `PSQL_URL="${DB_URL/+asyncpg/}"`;
  - запускает `psql` с `-v ON_ERROR_STOP=1`;
  - останавливается на любой ошибке миграции с `RESULT=FAIL` и `exit 1`.
- В конце всегда печатает:
  - `RESULT=OK|FAIL`
  - `LOG_PATH=/.../zumbot_deploy_check_*.log`

## Где смотреть лог и что отправлять в поддержку / ChatGPT

1. Сразу после запуска возьмите `LOG_PATH` из финального вывода скрипта.
2. Приложите:
   - полный блок `SUMMARY + RESULT + LOG_PATH`;
   - последние строки лога:

```bash
tail -n 200 <LOG_PATH>
```

3. Если упали миграции, приложите:
   - строку `[FAIL] Run SQL migrations - ...`;
   - stderr от `psql` из лога;
   - имя проблемного SQL-файла.

## Дополнительная диагностика

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

```bash
curl -fsS http://127.0.0.1:8000/healthz && echo
curl -fsS http://127.0.0.1:8000/readyz && echo
```

```bash
python /opt/zumbot/backend/scripts/export_logs.py --help
```
