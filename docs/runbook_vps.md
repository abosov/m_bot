# VPS runbook: ручной деплой без автодеплоя

> Автодеплой из GitHub Actions **не используем**. Прод-деплой выполняется вручную на VPS.

## Базовые пути

- Репозиторий: `/opt/zumbot/backend`
- Venv: `/opt/zumbot/backend/.venv`
- Env: `/etc/zumbot/backend.env`
- Деплой-скрипт: `/opt/zumbot/backend/scripts/vps_deploy.sh`
- Check-скрипт: `/opt/zumbot/backend/scripts/vps_deploy_check.sh`

## Одна команда для деплоя

```bash
sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy.sh'
```

Что делает команда:
- `git fetch` + `git pull --ff-only origin main`;
- `pip install -r requirements.txt` в `.venv` от пользователя `zumbot`;
- загрузка env из `/etc/zumbot/backend.env`;
- запуск SQL-миграций (`scripts/db_migrate.sh`);
- `systemctl restart zumbot-backend.service`;
- короткий wait `/readyz`;
- запуск пост-проверок (`scripts/vps_deploy_check.sh`).

## Только проверить без деплоя

```bash
sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh'
```

`vps_deploy_check.sh` делает **только проверки** (без `git pull`, `pip install`, миграций и рестарта).

## Где смотреть логи

- Лог деплоя: `/tmp/zumbot_deploy_*.log`
- Логи сервиса:

```bash
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```

## Быстрый triage при проблемах

1. Возьмите путь к логу из вывода `vps_deploy.sh`.
2. Отправьте:

```bash
tail -n 200 /tmp/zumbot_deploy_<timestamp>.log
sudo journalctl -u zumbot-backend.service -n 300 --no-pager
```
