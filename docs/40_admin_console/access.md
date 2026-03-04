# Admin Console Access Runbook

## 1. Scope

Admin Console — внутренний интерфейс. Он **не публикуется во внешний интернет** и не должен иметь публичный routing.

Базовый безопасный вариант доступа: SSH tunnel к backend на `127.0.0.1:8000`.

Если `/admin` всё же доступен публично на `zumbot.ru`, он **обязательно** должен быть защищён на уровне reverse proxy (Nginx Basic Auth) + backend auth.

---

## 2. Конфигурация backend-доступа

- `ADMIN_API_KEY` — ключ для admin API (`/admin/logs`, `/admin/specialists`, `/admin/heartbeats` и т.д.).
- `ADMIN_UI_PASSWORD` — пароль для browser-login в HTML UI (`/admin/login` и `/admin`).
- Если `ADMIN_UI_PASSWORD` не задан, UI использует fallback на `ADMIN_API_KEY`.
- Если не заданы **оба** значения (`ADMIN_UI_PASSWORD` и `ADMIN_API_KEY`) — UI маршруты `/admin` и `/admin/login` отключены (возвращают `404`).

> Не добавляйте реальные секреты в документацию, чаты, тикеты или скриншоты.

---

## 3. Nginx защита `/admin` через Basic Auth (VPS)

> Изменения Nginx обычно хранятся в infra-репозитории. Если конфиг не versioned в текущем репо, используйте команды ниже как операционный runbook.

### 3.1 [VPS] Создать htpasswd-файл

Установите утилиту (если отсутствует):

```bash
sudo apt-get update && sudo apt-get install -y apache2-utils
```

Создайте файл `/etc/nginx/.htpasswd_admin` и пользователя (например, `adminops`):

```bash
sudo htpasswd -c /etc/nginx/.htpasswd_admin adminops
```

Добавить ещё одного пользователя без перезаписи файла:

```bash
sudo htpasswd /etc/nginx/.htpasswd_admin another_admin
```

Права:

```bash
sudo chown root:www-data /etc/nginx/.htpasswd_admin
sudo chmod 640 /etc/nginx/.htpasswd_admin
```

### 3.2 [VPS] Настроить `location /admin` и `location /admin/`

В server-блоке `zumbot.ru` добавьте (или обновите) отдельные location для `/admin` и `/admin/`:

```nginx
location = /admin {
    auth_basic "Restricted Admin";
    auth_basic_user_file /etc/nginx/.htpasswd_admin;

    proxy_pass http://127.0.0.1:8000/admin;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /admin/ {
    auth_basic "Restricted Admin";
    auth_basic_user_file /etc/nginx/.htpasswd_admin;

    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Важно:
- Upstream для admin-трафика остаётся backend на `127.0.0.1:8000`.
- Защищаем **оба** пути: и `/admin`, и `/admin/*`.

### 3.3 [VPS] Проверка и reload Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 4. Browser usage (публичный доступ через Nginx)

1. Откройте `https://zumbot.ru/admin/login`.
2. Сначала браузер попросит логин/пароль Nginx Basic Auth (`.htpasswd`).
3. Затем откроется backend-форма Admin UI login; введите `ADMIN_UI_PASSWORD` (или `ADMIN_API_KEY`, если fallback).
4. После входа откройте `https://zumbot.ru/admin`.

Таким образом действует двухслойная защита:
- слой 1: Nginx Basic Auth,
- слой 2: backend admin UI cookie login.

---

## 5. Пошаговый доступ через SSH tunnel (рекомендуется)

### Шаг 1. [Локально] Создать SSH tunnel до VPS

```bash
ssh -N -L 18000:127.0.0.1:8000 <user>@<vps-host>
```

### Шаг 2. [Локально] Открыть UI login в браузере

- `http://127.0.0.1:18000/admin/login`

Введите пароль `ADMIN_UI_PASSWORD` (или `ADMIN_API_KEY`, если отдельный UI пароль не задан).

После успешного логина backend выставляет cookie `admin_session`:
- `HttpOnly`
- `SameSite=Strict`
- `Secure` в production
- подписана HMAC и имеет TTL 12 часов

### Шаг 3. [Локально] Открыть `/admin` (HTML)

- `http://127.0.0.1:18000/admin`

Внутри `/admin` используйте верхнюю навигацию: `Overview | Specialists | Logs | Heartbeats`. Разделы `Logs` и `Heartbeats` загружают данные без перезагрузки страницы через UI JSON endpoints.

Если cookie отсутствует/невалидна, endpoint возвращает `404` (без редиректа), чтобы не раскрывать наличие admin UI.

UI разделы Observability (US-AD-6) также требуют валидную cookie `admin_session` и при её отсутствии/невалидности возвращают `404`:
- `GET /admin/ui/logs`
- `GET /admin/ui/heartbeats`


UI Logs examples:
- Browser URL (после логина): `http://127.0.0.1:18000/admin/ui/logs?limit=20&is_error=true`
- Browser URL с фильтрами: `http://127.0.0.1:18000/admin/ui/logs?since=2026-03-01T00:00:00Z&until=2026-03-01T23:59:59Z&specialist_id=<SPECIALIST_UUID>`

Пример `curl` к UI endpoint с cookie (для диагностики; redaction всегда включён):

```bash
curl -i \
  -H 'Cookie: admin_session=<ADMIN_SESSION_COOKIE>' \
  'http://127.0.0.1:18000/admin/ui/logs?limit=5&is_error=true'
```



UI Heartbeats examples:
- Browser URL (после логина): `http://127.0.0.1:18000/admin/ui/heartbeats?limit=20`
- Browser URL с фильтром: `http://127.0.0.1:18000/admin/ui/heartbeats?service_name=worker&since=2026-03-01T00:00:00Z`

Пример `curl` к UI heartbeats endpoint с cookie:

```bash
curl -i \
  -H 'Cookie: admin_session=<ADMIN_SESSION_COOKIE>' \
  'http://127.0.0.1:18000/admin/ui/heartbeats?limit=5&service_name=worker'
```


## 5.1 Admin Actions (US-AD-7)

На странице Specialist Detail (`/admin/specialists/{id}`) доступна панель **Admin Actions**:

- `Disable` — отключить специалиста;
- `Enable` — включить обратно;
- `Reset OAuth` — сбросить OAuth-связку;
- `Change tariff` — выбрать новый тариф и применить.

Порядок использования:
1. Откройте карточку специалиста из раздела Specialists.
2. В блоке **Admin Actions** выберите нужное действие.
3. Подтвердите действие в браузерном `confirm()` диалоге.
4. После успеха страница автоматически перечитывает detail JSON (`GET /admin/ui/specialists/{id}`).

CSRF note:
- Для всех `POST /admin/ui/*` действий UI отправляет `X-CSRF-Token`.
- Значение токена берётся из cookie `admin_csrf` (double-submit pattern).
- Не вставляйте CSRF token/cookies/пароли в баг-репорты, скриншоты и публичные каналы.

Safety notes:
- System accounts (`is_system=true`) защищены от разрушительных действий (например, disable/reset/tariff change возвращают `403`).
- Любое действие пишется в `admin_audit_log` (success/failed) для форензики.
- Ответы Admin Actions не содержат OAuth token-ов и других секретов.

### Шаг 4. [Локально] Проверить admin API по `X-API-Key`

UI cookie **не заменяет** API-ключ для JSON endpoint-ов:

```bash
curl -i \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  'http://127.0.0.1:18000/admin/logs?limit=5'
```

```bash
curl -i \
  -H 'X-API-Key: <ADMIN_API_KEY>' \
  'http://127.0.0.1:18000/admin/heartbeats?limit=5'
```

---

## 6. Security notes


US-AD-6 specific:
- `GET /admin/ui/logs` и `GET /admin/ui/heartbeats` используют только cookie `admin_session`; `X-API-Key` для них не требуется.
- Для UI observability endpoint-ов невалидная/отсутствующая cookie и запросы с `Accept: text/html` должны отвечать `404`.
- Для UI logs redaction всегда принудительный; попытки `redact=false` не должны отключать маскирование.
- Не публикуйте `/admin/ui/*` наружу; используйте только внутренний доступ (SSH tunnel / защищённый private routing).

- Не логируйте `ADMIN_API_KEY`, `ADMIN_UI_PASSWORD`, cookie `admin_session`.
- Не храните `.htpasswd` в git-репозитории.
- Не вставляйте реальные секреты в скриншоты, записи экрана и публичные каналы.
- Для демонстраций используйте только плейсхолдеры.
