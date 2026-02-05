# Enums (MVP)

Документ фиксирует перечисления (enum-like значения), используемые в базе данных.

---

## 1) specialist.status
Состояние specialist как тенанта платформы.

- `onboarding` — специалист в процессе подключения (US-01 не завершён)
- `active` — специалист подключён и может принимать записи
- `suspended` — отключён/заблокирован (не MVP-логика, но значение зарезервировано)

---

## 2) telegram_bot.status
Состояние подключения Telegram-бота специалиста.

- `active` — бот валиден, webhook установлен
- `error` — ошибка подключения (неверный токен / webhook не установился)

---

## 3) google_oauth.status
Состояние подключения Google OAuth.

- `connected` — refresh token сохранён
- `revoked` — доступ отозван (зарезервировано)
- `error` — ошибка подключения (зарезервировано)

---

## 4) specialist_calendar.source
Как был получен календарь.

- `selected` — выбран существующий календарь
- `created` — календарь создан платформой

---

## 5) client.timezone_source
Источник значения timezone клиента.

- `default_from_specialist` — установлен по умолчанию = specialist_timezone
- `client_selected` — выбран клиентом вручную

---

## 6) appointment.booking_state
Бизнес-состояние записи (см. booking_state_machine).

- `pending` — выбран слот, идёт попытка создать событие в Google
- `confirmed` — событие создано в Google
- `failed` — создать событие не удалось
- `canceled_by_client` — отменено клиентом
- `canceled_by_specialist` — отменено специалистом

---

## 7) oauth_state.type
Тип одноразового state для OAuth.

- `google_connect` — подключение Google (онбординг)
- `google_reconnect` — переподключение Google (позже)

---

## Примечания
- В MVP избегаем сложных enum для retry/backoff, так как нет воркеров.
- Дополнительные статусы (rescheduled, syncing, etc.) будут добавлены позже при расширении.
