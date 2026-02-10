# Secrets and Encryption (MVP)

Документ фиксирует:
- какие секреты существуют в системе,
- где они хранятся,
- какие данные должны быть зашифрованы,
- минимальные требования безопасности для запуска MVP.

---

## 1. Секреты инфраструктуры (env / secret storage)

Обязательные переменные окружения (production):

### Telegram
- `MASTER_BOT_TOKEN` — токен master_bot

### Google OAuth
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` — `https://api.zumbot.ru/google/oauth/callback`

### Backend
- `BASE_URL` — публичный домен backend (`https://api.zumbot.ru`)
- `PUBLIC_SITE_URL` — публичный сайт/лендинг (`https://zumbot.ru`)
- `DB_URL` — строка подключения к БД
- `ENCRYPTION_KEY` — ключ для шифрования чувствительных данных
- `ADMIN_API_KEY` — ключ для закрытого admin API (опционально; если не задан, эндпоинты скрыты)

### Настройки (конфиг)
Параметры ниже зарезервированы под будущие оптимизации и
**пока не используются в коде** (planned/TODO):
- `TIMEZONE_TTL_HOURS` (например 6)
- `GOOGLE_RETRY_COUNT` (например 3)
- `GOOGLE_REQUEST_TIMEOUT_SEC` (например 5)

### Локальная разработка
- локальные значения держим в `.env.local` (не коммитится)
- `APP_ENV=local` включает загрузку `.env.local` с `override=True`
- если `APP_ENV` не задан, среда автоматически определяется как `local`, когда `.env.local` найден
- в репозитории хранится `.env.example` с шаблоном без секретов
- на VPS `.env.local` не используется: секреты передаются только через окружение сервиса

---

## 2. Что хранить в базе данных только зашифрованно

### 2.1 Telegram bot tokens
- `telegram_bot.bot_token_encrypted`

Причина:
- компрометация токена = полный контроль над ботом

### 2.2 Google refresh token
- `google_oauth.refresh_token_encrypted`

Причина:
- refresh token позволяет получать access token и доступ к календарю

---

## 3. Модель шифрования (MVP)

Минимальные требования:
- симметричное шифрование на уровне приложения
- ключ шифрования хранится только в секретах окружения (`ENCRYPTION_KEY`)
- данные в БД хранятся в зашифрованном виде и не должны быть читаемы без ключа

Рекомендация:
- использовать проверенную библиотеку шифрования
- хранить вместе с ciphertext метаданные (версия/nonce), если требуется
- предусмотреть ротацию ключа в будущем (зарезервировано)

---

## 4. Webhook secret

### 4.1 Назначение
Webhook URL содержит секрет:
`/tg/webhook/{bot_id}/{secret}`

Этот секрет:
- не является “токеном Telegram”
- нужен для того, чтобы никто не мог отправить фальшивые updates в webhook

### 4.2 Хранение
- `telegram_bot.webhook_secret` хранится в БД (можно без шифрования, но как секрет)
- не выводится в логи
- не показывается пользователю

---

## 5. Логирование и секреты

Запрещено логировать:
- bot_token
- refresh_token
- encryption key
- OAuth authorization code

Политика redaction (зафиксировано в коде):
- `/admin/logs` использует `redact=true` по умолчанию;
- в production `redact=false` запрещён (`403`);
- секреты не должны попадать в `message_logs`, export и admin logs в открытом виде.


Дополнительное обязательное правило для reverse-proxy (nginx):
- для маршрута `/tg/webhook/{bot_id}/{secret}` **нельзя** логировать полный URI
  (`$request_uri`/`$uri?$args`), потому что путь содержит `webhook_secret`;
- в access-лог должен попадать только маскированный путь вида
  `/tg/webhook/<bot_id>/***`;
- query string для webhook-запросов не логируется.

Рекомендованная схема настройки:
1. `map $uri $sanitized_path` — подмена секрета в 4-м сегменте пути на `***`.
2. `log_format` использует `$sanitized_path` (а не `$request_uri`).
3. `access_log` для API использует этот `log_format`.
4. после изменений обязательно выполнить `nginx -t` и reload.

Пример (минимально необходимый):
```nginx
map $uri $sanitized_path {
    default $uri;
    ~^/tg/webhook/([0-9]+)/[^/]+$ /tg/webhook/$1/***;
}

log_format api_main
    '$remote_addr - [$time_local] '
    '"$request_method $sanitized_path $server_protocol" $status $body_bytes_sent';

server {
    listen 443 ssl;
    server_name api.example.com;

    access_log /var/log/nginx/api_access.log api_main;

    location /tg/webhook/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Проверка после релоуда:
- отправить тестовый POST на webhook URL;
- убедиться, что в access-логе нет исходного `webhook_secret`,
  а записан только `/tg/webhook/<bot_id>/***`.

Разрешено логировать:
- `specialist_id`
- `bot_id`
- `calendar_id`
- коды ошибок (HTTP status, error codes)
- “обезличенные” события домена (booking confirmed/failed и т.п.)

---

## 6. Доступы и права (операционный минимум)

- доступ к секретам окружения имеет только команда/оператор (super_admin)
- доступ к БД ограничен
- резервные копии БД должны храниться защищённо
- доступ к логам ограничен

---

## 7. Threat model (минимум)

Основные риски:
- утечка bot_token → захват бота
- утечка refresh_token → доступ к календарю specialist
- подмена webhook updates → мошеннические записи

MVP меры:
- шифрование токенов
- webhook_secret в URL
- TLS для всех запросов
- минимальные таймауты и ограничения

---

## Связанные документы
- `50_integrations/telegram.md`
- `50_integrations/google_calendar.md`
- `30_architecture/deployment.md`
- `40_data_model/schema.md`
