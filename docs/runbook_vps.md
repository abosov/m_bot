# VPS runbook: deploy + health + diagnostics

Этот runbook описывает один безопасный способ проверить деплой и собрать диагностику на VPS.

## 1) Предусловия

- Репозиторий backend находится в `/opt/zumbot/backend`.
- Есть виртуальное окружение `/opt/zumbot/backend/.venv`.
- Есть файл окружения `/etc/zumbot/backend.env`.
- systemd unit: `zumbot-backend.service` (и опционально `zumbot-backend.socket`).

## 2) Как запускать

Запускать **только от root**:

```bash
sudo bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

Опционально можно проверить внешний домен (health/ready):

```bash
sudo ZUMBOT_DOMAIN_BASE_URL="https://api.zumbot.ru" bash /opt/zumbot/backend/scripts/vps_deploy_check.sh
```

## 3) Что делает скрипт

Скрипт выполняет шаги:

1. Проверка структуры (`/opt/zumbot/backend`, `.venv`, `/etc/zumbot/backend.env`).
2. `git fetch` + `git pull --ff-only` под пользователем `zumbot`.
3. `pip install -r requirements.txt` в `.venv` под `zumbot`.
4. Прогон SQL-миграций из `scripts/migrations/*.sql`.
5. `systemctl daemon-reload` и restart `zumbot-backend.service`.
6. Проверки `/healthz` и `/readyz` локально (+ через домен, если задан).
7. `pytest` в `APP_ENV=test` с временным `ENCRYPTION_KEY`.
8. Диагностика: `systemctl status`, `journalctl`, `nginx -t`, `scripts/db_snapshot.sh`.

Весь вывод пишется в единый лог-файл:

- `/tmp/zumbot_deploy_YYYYmmdd_HHMMSS.log`

В конце скрипт печатает:

- `RESULT=OK` или `RESULT=FAIL`
- `LOG_PATH=/tmp/zumbot_deploy_...log`

## 4) Что нельзя запускать от root в репозитории

Чтобы не сломать права на файлы в git-дереве, **не запускайте от root**:

- `pip install -r requirements.txt` внутри `/opt/zumbot/backend`
- `pytest` внутри `/opt/zumbot/backend`
- `git pull`, `git checkout`, `git clean` внутри `/opt/zumbot/backend`

Эти команды должны идти от пользователя `zumbot`.

## 5) Что отправлять для диагностики

Если `RESULT=FAIL`:

1. Пришлите путь из `LOG_PATH`.
2. Приложите сам лог-файл целиком (`/tmp/zumbot_deploy_*.log`).
3. Не отправляйте `/etc/zumbot/backend.env` и любые секреты.
