# VPS runbook: деплой и диагностика одной командой

> Прод-деплой выполняется вручную на VPS.

## Базовые пути

- Репозиторий: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- Скрипт: `/opt/zumbot/backend/scripts/vps_deploy_check.sh`

## Ручной деплой (основной путь)

### Деплой (pull + install + migrations + restart + checks)

```bash
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh --mode deploy
```

### Проверка состояния после деплоя (checks)

```bash
sudo bash /opt/zumbot/backend/scripts/vps_deploy_check.sh --mode checks
```

Режим `checks` не делает `git pull`, `pip install`, миграции и рестарт, только проверяет состояние.

## Что делает скрипт

- запускает user-шаги от `zumbot` (git/pip/psql);
- запускает root-шаги только там, где нужно (`systemctl`, `nginx -t`);
- для psql использует URL без драйвера `+asyncpg`;
- SQL-миграции запускаются с `ON_ERROR_STOP=1`, при любой ошибке шаг завершается с `[FAIL]` и `exit 1`;
- не печатает секреты: URL в логах маскируется (`user:***@host`).

## Как прогнать проверки вручную

```bash
APP_ENV=test pytest -q
```

```bash
bash -n /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

## Как собрать логи и дамп

После запуска скрипта возьмите `LOG_PATH` из финального вывода:

```bash
tail -n 200 <LOG_PATH>
```

Сервисные логи:

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

Экспорт бизнес-логов:

```bash
python /opt/zumbot/backend/scripts/export_logs.py --help
python /opt/zumbot/backend/scripts/export_logs.py --source message_logs --since 2026-01-01T00:00:00Z --limit 500 --redact --out /tmp/message_logs.jsonl
```

SQL-снимок БД (без секретов в логе и без `\restrict`/`\unrestrict` в дампе по умолчанию):

```bash
bash /opt/zumbot/backend/scripts/db_snapshot.sh --days 7 --out /tmp/zumbot_logs_dump.sql
```

Если нужен «сырой» дамп pg_dump для отладки, добавьте `--raw`.

## Откат

1. В каталоге репозитория переключиться на прошлый стабильный коммит/тег.
2. Повторить деплой одной командой в `--mode deploy`.
3. Проверить `/healthz` и `/readyz`.

Пример:

```bash
sudo -u zumbot bash -lc 'cd /opt/zumbot/backend && git log --oneline -n 10'
sudo -u zumbot bash -lc 'cd /opt/zumbot/backend && git checkout <stable_commit>'
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh --mode deploy
```

## Мини-инструкция для пользователя (без знания архитектуры)

1. Подключитесь к серверу по SSH.
2. Выполните одну команду:

```bash
sudo VERBOSE=1 bash /opt/zumbot/backend/scripts/vps_deploy_check.sh --mode deploy
```

3. В конце скрипт покажет `RESULT` и `LOG_PATH`.
4. Если `RESULT=FAIL`, отправьте в поддержку:
   - путь `LOG_PATH`;
   - вывод `tail -n 200 <LOG_PATH>`;
   - вывод `sudo journalctl -u zumbot-backend.service -n 300 --no-pager`.
