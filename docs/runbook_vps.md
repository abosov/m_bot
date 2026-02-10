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


## Heartbeat throttling и интерпретация health/readiness

`/readyz` может вызываться часто (monitoring, LB, ручные проверки), поэтому запись
в `service_heartbeats` дросселируется переменной `HEARTBEAT_WRITE_INTERVAL_SEC`.

Контракт:
- readiness вычисляется на **каждый** запрос `/readyz` (проверка БД + event loop);
- запись в `service_heartbeats` создаётся не на каждый запрос, а не чаще чем раз в
  `HEARTBEAT_WRITE_INTERVAL_SEC`;
- если запросы приходят чаще интервала, часть запросов не создаёт новую запись в БД;
- это нормальное поведение и не считается потерей readiness-данных.

Когда heartbeat обновляется:
- первый проход после старта сервиса;
- очередной `/readyz`, когда истёк интервал throttling;
- следующий допустимый запрос после окна throttling.

Когда heartbeat **не** обновляется:
- `/readyz` приходит раньше, чем истёк `HEARTBEAT_WRITE_INTERVAL_SEC`;
- нет смены окна записи (обычный режим частых probes).

Влияние на диагностику:
- для текущего статуса используйте HTTP-код/тело `/readyz` и `/healthz`;
- для истории во времени используйте `service_heartbeats`, учитывая, что это
  дискретные точки с дросселированием, а не лог каждого probe-запроса.

Проверка после деплоя:
```bash
# 1) Быстрые вызовы /readyz (например, 5-10 раз подряд)
for i in {1..10}; do curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/readyz; done

# 2) Проверяем, что HTTP 200/503 возвращается корректно,
#    но число новых записей в service_heartbeats меньше числа вызовов.
```

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
