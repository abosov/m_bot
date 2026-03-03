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

Если cookie отсутствует/невалидна, endpoint возвращает `404` (без редиректа), чтобы не раскрывать наличие admin UI.

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

- Не логируйте `ADMIN_API_KEY`, `ADMIN_UI_PASSWORD`, cookie `admin_session`.
- Не храните `.htpasswd` в git-репозитории.
- Не вставляйте реальные секреты в скриншоты, записи экрана и публичные каналы.
- Для демонстраций используйте только плейсхолдеры.
