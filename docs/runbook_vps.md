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

`vps_deploy_check.sh` в режиме `checks` делает только проверки (без `git pull`, `pip install`, миграций и рестарта).

`vps_deploy_check.sh --mode deploy` выполняет ручной деплой и затем пост-проверки:
- `git fetch` + `git pull --ff-only origin main`;
- `pip install -r requirements.txt` в `.venv` от пользователя `zumbot`;
- загрузка env из `/etc/zumbot/backend.env`;
- запуск SQL-миграций (`scripts/db_migrate.sh`);
- `systemctl restart zumbot-backend.service`;
- ожидание `/readyz`;
- запуск пост-проверок.

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

## Troubleshooting

1. Найдите последний лог:  
   `ls -1t /tmp/zumbot_deploy_*.log | head -n 1`
2. Если запуск уже завершён, можно взять `LOG_PATH` из последних строк вывода скрипта.
3. Для диагностики пришлите:

```bash
tail -n 200 <LOG_PATH>
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```
