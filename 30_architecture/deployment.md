# Deployment (MVP)

Документ описывает минимальные требования к развёртыванию backend-сервиса
для корректной работы Telegram webhooks и Google OAuth.

---

## 1. Среды (environments)
Минимальный набор:
- `prod` — рабочая среда на VPS (виртуальный сервер)
- `staging` (опционально) — тестовая, если нужна для отладки
- `local` — локальная разработка (по умолчанию `/readyz` отключён)

В MVP допустимо начать с одной `prod`, но предусмотреть возможность добавить `staging` позже.

### Local vs VPS (простыми словами)
- **Local** — запуск на своём ноутбуке. Допускается `.env.local`.
- **VPS** — запуск на сервере с публичным доменом и HTTPS. `.env.local` запрещён.
- `APP_ENV=local` включает подхват `.env.local`.
- Если `APP_ENV` не задан, среда определяется автоматически:
  - есть `.env.local` → `local`;
  - нет `.env.local` → `prod`.

---

## 2. Домен и TLS
Требования:
- backend должен быть доступен по HTTPS (TLS обязателен для Telegram webhook и Google OAuth callback).
- требуется публичный домен backend:
  - `https://api.zumbot.ru`
- публичный сайт/лендинг (если используется):
  - `https://zumbot.ru`

---

## 2.1 Production деплой на VPS (PostgreSQL + systemd + nginx + TLS)
Рекомендуемый стек:
- PostgreSQL (локально на VPS или managed).
- systemd для запуска приложения.
- nginx как reverse proxy.
- TLS от Let's Encrypt (certbot).

Минимальная схема:
1) Поднять PostgreSQL и создать БД/пользователя.
2) Настроить сервис systemd, который запускает `python main.py`.
3) Настроить nginx:
   - проксировать `https://api.zumbot.ru` на `127.0.0.1:<WEB_PORT>`;
   - проксировать `https://zumbot.ru` на публичный фронтенд (статик/отдельный сервис).
4) Получить и обновлять TLS-сертификаты (Let's Encrypt).

Важно:
- Код **одинаковый** для local/prod.
- Все различия — только через переменные окружения.
- `.env.local` запрещён на VPS.

---

## 3. Конкурентность и влияние задержек

### Проблема
В MVP создание событий в Google выполняется синхронно (без воркеров).
Если Google отвечает медленно, запрос webhook может занимать секунды.

### Минимальная защита (обязательно)
- Запуск backend с конкурентностью:
  - несколько worker-процессов или async модель
- Это позволяет одному “долгому” запросу не блокировать остальных пользователей.


### Таймауты (обязательно)
- таймауты на внешние запросы к Google Calendar API:
  - короткие (например 3–5 секунд)
- ограничение числа попыток:
  - дефолт 3 попытки в рамках запроса

Идея:
- лучше корректно вернуть пользователю “не получилось, повторите позже”,
  чем зависнуть и потерять управляемость.


Минимальные требования MVP:
- backend должен поддерживать конкурентную обработку webhook-запросов
  (минимум 2 параллельных запроса),
  чтобы один медленный запрос к Google не блокировал остальных пользователей.



---

## 4. Переменные окружения / секреты

### Обязательные настройки
- `APP_ENV=prod`
- `MASTER_BOT_TOKEN` (секрет)
- `DB_URL` (секрет)
- `ENCRYPTION_KEY` (секрет для шифрования токенов)
- Google OAuth:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REDIRECT_URI` (`https://api.zumbot.ru/google/oauth/callback`)
- `BASE_URL` (публичная база URL backend для формирования webhook/oAuth ссылок) — `https://api.zumbot.ru`
- `PUBLIC_SITE_URL` (публичный сайт/лендинг) — `https://zumbot.ru`
- `TIMEZONE_TTL_HOURS` (например 6)
- `GOOGLE_RETRY_COUNT` (например 3)
- `ENABLE_READYZ` (опционально, переопределяет дефолт: `true` на VPS/prod, `false` локально)
Дополнительно для деплоя:
- `WEB_HOST` (по умолчанию `127.0.0.1` в prod)
- `WEB_PORT` (по умолчанию `8000`)
- `ADMIN_API_KEY` (опционально, включает закрытый admin API `/admin/*`)

### Что хранить в БД (зашифрованно)
- `telegram_bot.bot_token_encrypted`
- `google_oauth.refresh_token_encrypted`

---

## 5. База данных
Требования MVP:
- транзакции и уникальные индексы (для idempotency)
- резервное копирование (минимум ежедневно)

### Snapshot/backup логов (SQLite/PostgreSQL)
Используйте `scripts/db_snapshot.sh`. Пароли не хранятся в скрипте —
используйте `PGHOST/PGUSER/PGPASSWORD/PGDATABASE` или `.pgpass`.

```bash
# SQLite
DB_URL=sqlite+aiosqlite:///./mvp.db scripts/db_snapshot.sh --out /tmp/zumbot_snapshot.db

# PostgreSQL (последние 7 дней)
DB_URL=postgresql+asyncpg://user@localhost:5432/zumbot \
  PGHOST=127.0.0.1 PGUSER=readonly PGDATABASE=zumbot \
  scripts/db_snapshot.sh --days 7 --out /tmp/zumbot_logs_dump.sql
```

### Безопасное скачивание на локальную машину
```bash
scp user@vps-host:/tmp/zumbot_snapshot.db ./zumbot_snapshot.db
scp user@vps-host:/tmp/zumbot_logs_dump.sql ./zumbot_logs_dump.sql
```

### Опционально: read-only роль для логов (PostgreSQL)
Рекомендуется завести роль только с `SELECT` на таблицы логов:
`message_logs`, `service_heartbeats`, `bot_health_checks`.

---

## 6. Логирование и мониторинг (минимум)
- логировать:
  - входящие updates (без чувствительных данных)
  - ошибки Google API (код + сообщение без токенов)
  - ключевые события домена:
    - onboading started/completed
    - booking pending/confirmed/failed
    - cancel actions
- метрики (минимум):
  - количество ошибок Google
  - среднее время обработки webhook
  - количество confirmed/failed бронирований

В MVP мониторинг может быть “простым” (логи + алерты по ошибкам).

План по замене мониторинга:
- **MVP:** используем GH Actions cron как временный uptime-мониторинг.
- **После появления VPS:** переключаемся на внешний uptime-сервис
  (UptimeRobot/BetterStack), который делает `GET /readyz`
  и уведомляет при статусе не `200`.
- **Код менять не нужно** — только настройка внешнего мониторинга.

Локально `/readyz` по умолчанию отключён и отсутствует (404),
чтобы не требовать БД/loop-check в разработке.

### Health/ready usage
- `/healthz` — проверка живости сервиса (liveness), используется для простых проверок доступности.
- `/readyz` — проверка готовности (readiness), используется мониторингом и балансировщиком.
- В проде `/readyz` должен быть включён и опрашиваться внешним мониторингом.

### Лучшие практики
- Код **не меняется** между средами.
- Меняются **только** переменные окружения и конфигурация деплоя.
- `.env.local` используется **только** для local и **никогда** не копируется на VPS.

---

## 7. Webhook lifecycle

### Master bot webhook
- устанавливается один раз при развёртывании или вручную
- указывает на `/tg/webhook/{master_bot_id}/{secret}`

### Personal bots webhooks
- устанавливаются при онбординге specialist (US-01)
- webhook URL:
  `/tg/webhook/{bot_id}/{webhook_secret}`

---

## 8. Google OAuth setup
- в Google Cloud Console должны быть:
  - включён Google Calendar API
  - настроен OAuth consent screen
  - указан redirect URI: `https://api.zumbot.ru/google/oauth/callback`

---

## 9. Обновления и совместимость
- при изменении структуры БД использовать миграции
- при изменении webhook URL схемы:
  - нужна процедура переподключения webhooks для already connected bots (не MVP)

---

## 10. Ограничения MVP
- нет фоновых задач и очередей
- нет периодической синхронизации данных с Google
- reconcile выполняется on-demand в ключевых местах (слоты, мои записи)
