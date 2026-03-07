# Telegram → Google Calendar Booking Platform (MVP)

Этот репозиторий содержит **архитектуру, логику и модель данных** сервиса
для записи клиентов на консультации специалистов через Telegram-ботов
с интеграцией в Google Calendar.

Документация описывает **реальный рабочий MVP**, а не абстрактную схему.

---

## 1. Что это за система

Платформа позволяет:
- specialist подключить свой Google Calendar,
- создать личный Telegram-бот для клиентов,
- дать клиентам возможность записываться на консультации,
- автоматически фиксировать записи в Google Calendar.

Особенности MVP:
- один backend обслуживает **много Telegram-ботов**

Google Calendar — источник истины для:
- фактической занятости (busy/free),
- таймзоны календаря.

База данных платформы — источник истины для
состояний записи и бизнес-логики.

- без отдельного job-worker/очереди (есть внутренняя background coroutine для heartbeat)
- без переноса записи (только отмена + новая запись)

---

## 2. Основные роли

- **super_admin** — владелец платформы, доступ ко всей архитектуре и БД
- **specialist** — специалист, который принимает клиентов
- **client** — конечный клиент специалиста

---

## 3. Как читать репозиторий

Рекомендуемый порядок чтения:

1. **00_overview/**
   - `glossary.md` — словарь терминов
2. **10_user_stories/**
   - сценарии использования (что делает пользователь)
3. **20_flows_and_state_machines/**
   - состояния, роли, таймзоны
4. **30_architecture/**
   - компоненты, endpoints, деплой
5. **40_data_model/**
   - enums и схема БД
6. **50_integrations/**
   - Telegram и Google Calendar
7. **60_security_and_compliance/**
   - секреты и персональные данные
8. **70_open_questions_and_todo.md**
   - что не входит в MVP
9. **80_mvp_launch_checklist.md**
   - чеклист запуска


---

## AI Development Rules

This repository follows a structured AI-assisted development workflow.

All Codex prompts must follow the rules defined in:

`docs/90_codex/CODEX_OPERATING_SYSTEM.md`

Key principles:
- SQL migrations are the single source of truth for database schema and DB defaults
- ORM models must not define DB defaults via `server_default`
- Python `default=...` is app-level behavior only and must not replace DB migration defaults
- One prompt = one atomic change
- Role-based development workflow
- Mandatory documentation updates
- Explicit deployment checks
- QA validation

---

## 4. Ключевые архитектурные решения (зафиксированы)

- ✅ единый backend, webhook-модель
- ✅ отдельный Telegram-бот на каждого specialist
- ✅ Google Calendar = мастер занятости и таймзоны
- ✅ client существует **только в контуре specialist** (вариант A)
- ✅ idempotency для защиты от дублей
- ✅ таймзоны клиента и специалиста учитываются корректно
- ❌ нет отдельного фонового worker-процесса/очереди
- ❌ нет переноса записи
- ❌ нет уведомлений

Все осознанные ограничения описаны в `70_open_questions_and_todo.md`.

---

## 5. Как вносить изменения в архитектуру

### Принцип
**Любое изменение фиксируется в документации.**

### Примеры:
- изменился алгоритм бронирования →  
  правим:
  - `US-03_client_booking_flow.md`
  - `booking_state_machine.md`

- добавилось новое поле в БД →  
  правим:
  - `40_data_model/schema.md`
  - при необходимости `enums.md`

- изменилось правило таймзон →  
  правим:
  - `timezones.md`
  - соответствующий user story

### Координация правок
При изменениях рекомендуется:
1. указать, **какой файл меняется**
2. что именно:
   - логика
   - данные
   - ограничения MVP
3. проверить влияние на:
   - user stories
   - state machine
   - data model

---

## 6. MVP ≠ финальная версия

Этот репозиторий:
- намеренно **не усложнён**
- создан для быстрого запуска
- допускает расширение без ломки базы

Все идеи “на потом” — в `70_open_questions_and_todo.md`.

---

## 7. Точка старта разработки

Если начинать писать код:
1. ориентироваться на **user stories**
2. реализовывать **US-01 → US-03 по порядку**
3. строго соблюдать `booking_state_machine.md`
4. не добавлять фичи вне MVP без фиксации в документации

---

## 8. Окружения (local/prod) и переменные окружения

### Как определяется среда
- По умолчанию приложение использует **переменные окружения ОС**.
- Если `APP_ENV=local` → дополнительно подхватывается `.env.local` (с `override=True`).
- Если `APP_ENV` **не задан**:
  - при наличии `.env.local` среда считается `local`;
  - если `.env.local` нет, среда считается `prod`.
- Выбранная среда и факт наличия `.env.local` логируются при старте (без секретов).

### Что такое `APP_ENV`
`APP_ENV` — это переключатель среды выполнения:
- `local` (также допускаются `dev`/`development`) — локальная разработка;
- `prod` (также допускается `production`) — продакшн на VPS (виртуальный сервер).

### Что такое `ENABLE_READYZ`
`ENABLE_READYZ` включает или отключает endpoint `/readyz`:
- по умолчанию `true` в `prod`;
- по умолчанию `false` в `local`;
- можно явно задать `ENABLE_READYZ=true/false`, чтобы переопределить дефолт.

### Где хранить `.env.local`
- `.env.local` хранится **в корне репозитория** локально.
- Файл **в gitignore** и **не коммитится**.
- На VPS `.env.local` **не используется** и не должен присутствовать.

### Как запускать локально
1. Создать `.env.local` в корне репозитория.
2. Минимально задать переменные (пример):
   - `APP_ENV=local` (по желанию, чтобы явно зафиксировать среду)
   - `MASTER_BOT_TOKEN=<token>`
   - `DB_URL=sqlite+aiosqlite:///./mvp.db` (или оставить пустым)
3. Запустить сервис:
   - `python main.py`
4. `/healthz` доступен всегда.
   `/readyz` будет **отключён**, пока не задано `ENABLE_READYZ=true`.

### Как запускать на VPS (prod)
1. `.env.local` **не используется**.
2. Все переменные окружения задаются через окружение сервиса
   (systemd/Docker/панель хостинга).
3. Обязательно задать `APP_ENV=prod` и необходимые секреты.
4. Запуск — через процесс-менеджер (systemd, Docker, supervisor).
5. `/readyz` включён по умолчанию, но может быть выключен через
   `ENABLE_READYZ=false`.

### Лучшие практики
- Код **не меняется** между средами.
- Меняются **только** переменные окружения и конфигурация деплоя.
- `.env.local` используется **только** для local и **никогда** не копируется на VPS.

---

## 9. Как задеплоить на VPS

Ниже — минимальная пошаговая инструкция для `https://api.zumbot.ru` (backend)
и `https://zumbot.ru` (публичный сайт).

1) **Подготовить VPS**
   - Установить Python, PostgreSQL, nginx, certbot.
2) **Настроить PostgreSQL**
   - Создать БД и пользователя.
   - Сформировать `DB_URL` (например `postgresql+asyncpg://user:pass@localhost:5432/zumbot`).
3) **Настроить переменные окружения**
   - Минимум для prod:
     - `APP_ENV=prod`
     - `DB_URL`
     - `MASTER_BOT_TOKEN`
     - `ENCRYPTION_KEY`
     - `GOOGLE_CLIENT_ID`
     - `GOOGLE_CLIENT_SECRET`
     - `GOOGLE_REDIRECT_URI=https://api.zumbot.ru/google/oauth/callback`
     - `BASE_URL=https://api.zumbot.ru`
     - `PUBLIC_SITE_URL=https://zumbot.ru`
     - `SUPPORT_TG_URL=https://t.me/zumbot_support` (optional)
     - `ENABLE_READYZ=true`
   - При необходимости задать `WEB_HOST` и `WEB_PORT`.
4) **Запуск приложения через systemd**
   - Сервис запускает `python main.py`.
   - Переменные окружения задаются в unit-файле или через EnvironmentFile.
5) **Настроить nginx**
   - `api.zumbot.ru` → прокси на `127.0.0.1:<WEB_PORT>`.
   - `zumbot.ru` → статик/отдельный фронтенд.

Подробный VPS-runbook (ручной деплой, smoke-check, базовая nginx-защита и fail2ban): `docs/runbook_vps.md`.
Nginx security snippet: `docs/snippets/nginx_security.conf`.
Логи runtime и упаковка для выгрузки: `docs/logging.md`. 
6) **Включить TLS**
   - Получить сертификаты через certbot для обоих доменов.
7) **Проверить health**
   - `GET https://api.zumbot.ru/healthz` → `200` + build info (`version`, `build_number`, `commit_sha`, `build_date_utc`).
   - `GET https://api.zumbot.ru/readyz` → `200` (если всё готово).

Важно:
- Код **не меняется** между local/prod.
- Все различия — только через переменные окружения.
- `.env.local` хранится только локально и **не копируется** на VPS.

Для воспроизводимого деплоя и диагностики на VPS используйте runbook:
- `docs/runbook_vps.md`
- `docs/runbook/contact-form.md` (форма `/contacts` и SMTP-настройка)
- скрипт `scripts/vps_deploy_check.sh`
- ручной workflow GitHub Actions: `.github/workflows/deploy_manual.yml` (только кнопка Run workflow, без автодеплоя)

Основные команды:
- checks: `sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh'`
- deploy: `sudo bash -lc 'cd /opt/zumbot/backend && bash scripts/vps_deploy_check.sh --mode deploy'`

---

## 10. Настройка Google OAuth

1) В Google Cloud Console:
   - включить Google Calendar API;
   - настроить OAuth consent screen;
   - создать OAuth client.
2) Указать redirect URI:
   - `https://api.zumbot.ru/google/oauth/callback`
3) Для Telegram → Google OAuth использовать явный web-flow:
   1. Пользователь нажимает кнопку в Telegram.
   2. Бот присылает ссылку на `https://zumbot.ru/connect`.
   3. OAuth проходит на обычной странице браузера (без hidden iframe/WebApp OAuth).
   4. После успеха — redirect на `https://zumbot.ru/success`.
   5. Пользователь возвращается в Telegram.
4) В OAuth consent screen указать:
   - Authorized domain: `zumbot.ru`
   - Redirect URI: `https://api.zumbot.ru/google/oauth/callback` (или ваш backend-домен)
5) Токен web-connect передаётся через URL fragment и обменивается на сессию через `POST /auth/telegram/consume`.
   Требования безопасности: one-time TTL токена, HttpOnly+Secure cookie, отсутствие raw токена в логах.
6) Задать переменные окружения в prod:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI=https://api.zumbot.ru/google/oauth/callback`

---



## 11.1. Production migration-first policy

Для production схема БД должна изменяться **через SQL-миграции** (`scripts/migrations/*.sql`).
`init_db(create_all)` сохранён для обратной совместимости и локальной разработки,
но не рассматривается как основной путь обновления prod-схемы.

## 11. Регрессионные тесты (local/CI)

Перед деплоем в `main` и в CI рекомендуется запускать минимум:

```bash
pytest -q tests/test_webhook_endpoint.py
pytest -q tests/test_google_calendar_async.py
```

### Encoding guard (проверка кодировки)

Зачем это нужно:
- ранно ловит не-UTF-8 файлы и артефакты mojibake до релиза;
- защищает тексты интерфейса/документации от «кракозябр» после merge и деплоя;
- уменьшает риск неожиданных ошибок при обработке строк в runtime и в интеграциях.

Локальный запуск:

```bash
python scripts/check_encoding.py
```

Строгий режим (warning = fail):

```bash
python scripts/check_encoding.py --strict-warn
```

Что покрывают эти проверки:
- `tests/test_webhook_endpoint.py` — поведение webhook endpoint,
  включая негативные кейсы и ограничение payload (HTTP 413 для слишком больших тел).
- `tests/test_google_calendar_async.py` — ключевые асинхронные сценарии интеграции
  с Google Calendar API (timeout/error-handling на уровне сервиса).
  > Planned/TODO: явная стратегия retry для вызовов Google Calendar пока не описана
  > и не заявляется как реализованная в этом README.

При полном прогоне регрессии:
```bash
pytest -q
```

## 12. Контакт и владение

Владелец архитектуры и продукта:
- super_admin (автор проекта)

Документация — **часть продукта**, а не вторичный артефакт.

---

## Конец
Если этот README устарел — значит архитектура менялась,
а документация нет. Это считается ошибкой.

## 13. Политика путей в репозитории

Ранее в отдельных местах использовалась историческая заглушка `_!_` как замена `/` в путях (например, для имитации вложенных директорий). Теперь такой формат **запрещён**.

В проекте должны использоваться только реальные пути с директориями: `docs/...`, `scripts/...`, `handlers/...` и т.д.



### Smoke-checklist перед prod-релизом
- `GET /admin/login` при включённом admin UI возвращает `200` и форму логина.
- `POST /admin/login` с валидным паролем устанавливает cookie `admin_session` и даёт доступ к `GET /admin`.
- `GET /admin` без валидной cookie `admin_session` возвращает `404`.
- `/admin/logs` по умолчанию возвращает redacted-контент; в `APP_ENV=prod` запрос с `redact=false` должен вернуть `403`.
- `GET /google/oauth/callback` отклоняет повторно использованный или истёкший `state`.
- webhook-запрос c body больше `MAX_WEBHOOK_BODY_BYTES` получает `413 Payload Too Large`.

---

## Миграции на VPS

Для применения миграций используйте стабильную команду-обёртку:

```bash
bash scripts/run_migrations.sh
```

Скрипт запускается из любого `cwd`, подхватывает `DB_URL` из `/etc/zumbot/backend.env` (если не задан в окружении) и вызывает основной механизм миграций проекта.

### Migration notes: specialist confirmation backfill/compat

- Ручной backfill для старых `appointment.booking_state='confirmed'` **не требуется**.
- Исторические `confirmed` трактуются как уже подтверждённые специалистом и остаются валидными.
- Записи, созданные до ввода `awaiting_specialist_confirmation`, продолжают отображаться и работать без дополнительных действий с данными.

## Безопасный сброс smoke-данных

Для очистки тестовых Telegram-аккаунтов используйте команду-обёртку `zumbot-test-reset` (symlink на `scripts/test_data_reset_run.py`).

Реестр в production: `/etc/zumbot/test_accounts.yaml` (рекомендуемые права `600`, владелец `zumbot`).
Если системный реестр отсутствует, fallback: `config/test_accounts.yaml`.

Быстрый старт:
```bash
# dry-run по умолчанию
zumbot-test-reset

# реальное удаление: двойное подтверждение
zumbot-test-reset --apply --i-know-what-i-am-doing --yes
```

Скрипт автоматически подхватывает `DB_URL` из `/etc/zumbot/backend.env`.
Подробная инструкция и safety-алгоритм: `docs/test_data_reset.md`.

## 14. Эксплуатационные утилиты (кратко)

Для ежедневной ops-гигиены используйте:

- `scripts/check_orphan_specialist_media.sh` — проверить orphan-папки медиа специалистов на VPS (подробная инструкция в `docs/runbook_vps.md`, секция `Ops utility: проверка orphan media`).
- `scripts/clean_dev.sh` — локально очистить dev-артефакты (`__pycache__`, `.pytest_cache`, `.DS_Store`, `*.pyc`); подробная инструкция в `docs/runbook_vps.md`, секция `Ops utility: локальная очистка dev-артефактов`.

Операционные шаги и ограничения:
- VPS runbook: `docs/runbook_vps.md`.
- Назначение/ограничения media-cleanup: `docs/security/media_storage.md`.
- Назначение/ограничения dev-cleanup: `docs/test_data_reset.md`.

Политика защиты от мусора в Git зафиксирована в `.gitignore` (включая `.DS_Store`, `.pytest_cache`, `*.pyo`, `*.pyd`, `.vscode/`, `.idea/`, `*.log`).

### .gitignore hygiene (security + repository cleanliness)

Игнорируемые шаблоны operational/developer-мусора:
- `.DS_Store`;
- `.pytest_cache/`;
- `*.pyo`, `*.pyd`;
- `.vscode/`, `.idea/`;
- `*.log`.

Зачем это нужно:
- снижает риск случайного коммита локальных артефактов и служебных метаданных;
- уменьшает вероятность утечки чувствительного контекста через debug/log файлы;
- сохраняет историю Git чистой и ревью-пригодной (без шумовых файлов среды разработки).

Почему такие файлы не должны попадать в Git:
- они зависят от локальной машины/IDE и не являются частью продукта;
- часто быстро устаревают и создают дифф-шум;
- могут содержать диагностические данные, не предназначенные для хранения в репозитории.

Важно: `.gitignore`-гигиена предотвращает загрязнение репозитория,
но **не заменяет** серверные процедуры очистки/обслуживания на VPS.
