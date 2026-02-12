# Безопасный сброс тестовых данных smoke-аккаунтов

## Где хранить реестр
- Продакшен-реестр: `/etc/zumbot/test_accounts.yaml` (права `600`, владелец `zumbot`).
- Локальный fallback: `config/test_accounts.yaml` (не коммитится).
- Шаблон: `config/test_accounts.example.yaml`.

Формат:
```yaml
accounts:
  - name: smoke_specialist_1
    role: specialist_owner
    tg_user_id: 83691599
    notes: "optional"
  - name: smoke_client_1
    role: client
    tg_user_id: 123456789
notes: "optional global notes"
```

## Одна команда очистки (VPS)
Команда: `zumbot-test-reset` (symlink на `scripts/test_data_reset_run.py`).

Поведение обёртки:
- работает из любой текущей директории (cwd может быть любым);
- всегда запускает `scripts/test_data_reset.py` через python из `backend/.venv/bin/python3`;
- запускает дочерний процесс с `cwd=/opt/zumbot/backend` (repo_root), чтобы относительные пути были стабильными;
- автоматически читает `/etc/zumbot/backend.env` и подхватывает `DB_URL`;
- выбирает registry автоматически:
  1) `/etc/zumbot/test_accounts.yaml`,
  2) fallback `config/test_accounts.yaml`,
  3) иначе понятная ошибка;
- по умолчанию всегда `DRY-RUN`;
- для реального удаления нужно двойное подтверждение:
  - `--apply`,
  - `--i-know-what-i-am-doing`,
  - и `--yes` (или интерактивный prompt в TTY).

Поддерживаемые ключи (пробрасываются в Python CLI):
- `--registry PATH`
- `--names name1 name2 ...`
- `--tg-user-ids 111 222 ...`
- `--force`
- `--max-clients-threshold N`
- `--format json|text`

Примеры:
```bash
# dry-run (default)
zumbot-test-reset

# dry-run по конкретным именам
zumbot-test-reset --names smoke_specialist_1 smoke_client_1

# apply с явным подтверждением
zumbot-test-reset --apply --i-know-what-i-am-doing --yes

# apply выборочно
zumbot-test-reset --apply --i-know-what-i-am-doing --yes --tg-user-ids 83691599 123456789
```

## Низкоуровневый CLI (без обёртки)
Скрипт: `scripts/test_data_reset.py`.

Примеры:
```bash
python3 scripts/test_data_reset.py --dry-run
python3 scripts/test_data_reset.py --apply --registry /etc/zumbot/test_accounts.yaml
```

## Safety guards
По умолчанию (без `--force`):
- запрещено удалять specialist-скоуп для статусов вне `onboarding/active`;
- запрещено удалять specialist-скоуп, если число клиентов выше порога `--max-clients-threshold`;
- массовое удаление всех клиентов специалиста возможно только если его владелец указан в реестре с ролью `specialist_owner`.

`--force` отключает guard-проверки осознанно.

## Гарантия области удаления
Удаление ограничено scope’ом тестовых `tg_user_id` и связанных с ними `specialist_id/client_id`.
Данные других специалистов/клиентов не должны затрагиваться.
