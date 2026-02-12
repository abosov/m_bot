# Безопасный сброс тестовых данных smoke-аккаунтов

## Реестр аккаунтов
- Рабочий реестр: `config/test_accounts.yaml` (не коммитится).
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

Создание локального реестра:
```bash
cp config/test_accounts.example.yaml config/test_accounts.yaml
```

## Одна команда очистки
Скрипт: `scripts/test_data_reset.py`.

Поддерживаемые ключи:
- `--registry PATH` (по умолчанию `config/test_accounts.yaml`)
- `--dry-run` (по умолчанию, если не указан `--apply`)
- `--apply`
- `--names name1 name2 ...`
- `--tg-user-ids 111 222 ...`
- `--force`
- `--format json|text`
- `--list-registry`

Примеры:
```bash
python3 scripts/test_data_reset.py --dry-run
python3 scripts/test_data_reset.py --apply
python3 scripts/test_data_reset.py --apply --names smoke_specialist_1
python3 scripts/test_data_reset.py --dry-run --tg-user-ids 83691599
python3 scripts/test_data_reset.py --list-registry
```

## Алгоритм очистки
1. Берутся `tg_user_id` из реестра (или из `--tg-user-ids`).
2. Находятся target-специалисты:
   - `specialist_auth_telegram.tg_user_id -> specialist_id`.
   - `specialist_profile.owner_tg_user_id -> specialist_id`.
3. Находятся target-клиенты:
   - `client.tg_user_id -> client_id + specialist_id`.
4. Формируются цели очистки (`specialist_id`, `client_id`) строго в рамках выбранных `tg_user_id`.
5. Считается dry-run отчёт: какие `specialist_id/client_id` затронутся и сколько строк в каждой таблице.
6. Если `--apply`: удаление идёт в одной транзакции в порядке зависимостей:
   - `appointment`
   - `weekly_availability`
   - `specialist_calendar_settings` (+ legacy `specialist_calendar`, если таблица есть)
   - `google_oauth`, `oauth_state`
   - `telegram_bot`, `bot_health_checks`, `message_logs`
   - `client`
   - `specialist_profile`, `specialist_auth_telegram`
   - `specialist`

## Safety guards
По умолчанию (без `--force`):
- запрещено удалять specialist-скоуп для статусов вне `onboarding/active`;
- запрещено удалять specialist-скоуп, если число клиентов выше порога `--max-clients-threshold`;
- массовое удаление всех клиентов специалиста возможно только если его владелец указан в реестре с ролью `specialist_owner`.

`--force` отключает эти guard-проверки осознанно.

## Гарантия области удаления
Удаление ограничено scope’ом тестовых `tg_user_id` и связанных с ними `specialist_id/client_id`.
Данные других специалистов/клиентов не должны затрагиваться.
