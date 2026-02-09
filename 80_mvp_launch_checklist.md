# MVP Launch Checklist

Документ — практический чеклист запуска MVP.
Если все пункты выполнены, сервис **реально можно использовать** специалистами и клиентами.

---

## 1. Инфраструктура

### Сервер
- [ ] Backend развёрнут на публичном сервере
- [ ] Сервер доступен по HTTPS
- [ ] TLS-сертификат валиден (Telegram и Google принимают)
- [ ] `GET /healthz` возвращает `200 OK`
- [ ] `GET /readyz` возвращает `200 OK`
- [ ] Мониторинг проверяет `GET /readyz` (200 при доступной БД)
- [ ] GitHub Actions cron включён (uptime workflow)
- [ ] Uptime мониторинг (GitHub Actions) дергает `/readyz`

### После появления VPS
- [ ] Завести монитор в UptimeRobot/BetterStack на `GET /readyz`
- [ ] Настроить интервал и алерты (email/Telegram/Slack)
- [ ] Проверить, что `/readyz` возвращает 200 и пишет ServiceHeartbeat в БД
- [ ] Отключить GH Actions cron для uptime (оставить CI)

### Домен
- [ ] Настроен публичный домен backend `https://api.zumbot.ru`
- [ ] BASE_URL указывает на `https://api.zumbot.ru`
- [ ] PUBLIC_SITE_URL указывает на `https://zumbot.ru`

---

## 2. Google Cloud Console

### Проект
- [ ] Создан Google Cloud Project
- [ ] Включён Google Calendar API

### OAuth
- [ ] Настроен OAuth consent screen
- [ ] Тип приложения соответствует использованию (External)
- [ ] Добавлены scopes для Calendar
- [ ] Созданы OAuth credentials:
  - Client ID
  - Client Secret

### Redirect URI
- [ ] В Google указана `https://api.zumbot.ru/google/oauth/callback`

---

## 3. Telegram

### Master bot
- [ ] Создан master_bot через BotFather
- [ ] Получен `MASTER_BOT_TOKEN`
- [ ] Master bot добавлен в БД (или конфиг)
- [ ] Установлен webhook master_bot

### Personal bots
- [ ] Проверен сценарий:
  - ввод bot_token
  - `getMe`
  - установка webhook
- [ ] Проверено, что backend принимает updates от разных bot_id

---

## 4. Backend конфигурация

### Переменные окружения
- [ ] MASTER_BOT_TOKEN
- [ ] DB_URL
- [ ] ENCRYPTION_KEY
- [ ] GOOGLE_CLIENT_ID
- [ ] GOOGLE_CLIENT_SECRET
- [ ] GOOGLE_REDIRECT_URI
- [ ] BASE_URL
- [ ] PUBLIC_SITE_URL
- [ ] TIMEZONE_TTL_HOURS
- [ ] GOOGLE_RETRY_COUNT
- [ ] GOOGLE_REQUEST_TIMEOUT_SEC

---

## 5. База данных

### Схема
- [ ] Все таблицы из `40_data_model/schema.md` созданы
- [ ] Все enum соответствуют `40_data_model/enums.md`
- [ ] Уникальные индексы (idempotency!) присутствуют
- [ ] Таблицы `service_heartbeats` и `bot_health_checks` созданы

### Данные
- [ ] Проверено создание specialist
- [ ] Проверено создание client
- [ ] Проверено создание appointment

### Резервное копирование
- [ ] Настроен регулярный backup БД (минимум daily)
- [ ] Настроен отдельный snapshot/экспорт логов для поддержки (JSONL/CSV или SQL dump)

---

## 6. Онбординг specialist (US-01)

- [ ] /start в master_bot работает
- [ ] /status в master_bot работает и проверяет доступность personal bot (getMe)
- [ ] specialist создаётся в БД
- [ ] bot_token принимается и валидируется
- [ ] webhook personal bot устанавливается
- [ ] Google OAuth проходит успешно
- [ ] Можно выбрать существующий календарь
- [ ] Можно создать новый календарь
- [ ] Timezone календаря считывается и сохраняется
- [ ] Weekly availability сохраняется
- [ ] specialist.status становится `active`

---

## 7. Управление specialist (US-02)

- [ ] Бот корректно определяет owner
- [ ] specialist видит свои записи
- [ ] specialist может отменить запись
- [ ] specialist может добавить приватную заметку
- [ ] specialist может изменить расписание
- [ ] specialist может изменить длительность сессии
- [ ] specialist может задать минимальный технический перерыв между сессиями

---

## 8. Запись клиента (US-03)

### Первый вход
- [ ] /start создаёт client
- [ ] client вводит display_name
- [ ] client_timezone устанавливается корректно

### Слоты
- [ ] Слоты считаются по weekly availability
- [ ] Учитывается lead time (2 часа)
- [ ] Неделя считается в TZ клиента
- [ ] Занятость корректно фильтруется через Google

### Бронирование
- [ ] Создаётся appointment (pending → confirmed)
- [ ] Создаётся событие в Google Calendar
- [ ] Summary события соответствует формату
- [ ] Повторный клик не создаёт дубликат (idempotency)

### Ошибки
- [ ] Ошибка Google приводит к `failed`
- [ ] Retry работает
- [ ] Пользователь получает понятное сообщение

---

## 9. Отмена записи

- [ ] client может отменить запись >= 12 часов
- [ ] client не может отменить запись < 12 часов
- [ ] specialist может отменить запись
- [ ] Событие удаляется из Google Calendar

---

## 10. Timezones

- [ ] TZ specialist берётся из Google Calendar
- [ ] Изменение TZ в Google корректно обрабатывается
- [ ] Время отображается в TZ клиента
- [ ] При различии TZ показывается время specialist

---

## 11. Безопасность и приватность

- [ ] bot_token хранится зашифрованно
- [ ] refresh_token хранится зашифрованно
- [ ] webhook_secret проверяется
- [ ] В логах нет ПДн и секретов
- [ ] Доступ к логам ограничен (admin API только через SSH tunnel / readonly доступ)
- [ ] В Google Calendar нет лишних данных

---

## 12. Smoke test (обязательно)

Минимальный end-to-end сценарий:
1. Specialist проходит онбординг
2. Клиент записывается
3. Событие появляется в Google Calendar
4. Клиент отменяет запись
5. Событие исчезает из Google Calendar

---

## Итог
Если все пункты отмечены — MVP **готов к реальному использованию**.
