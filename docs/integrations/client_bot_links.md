# Интеграция: ссылки на клиентский Telegram-бот

Кнопка `Связаться со специалистом` в Hero формирует ссылку в формате:

`https://t.me/{client_bot_username}?start=write_{specialist_id}`

## Источник данных
Из `specialist_public_profile`:
- `client_bot_username`
- `specialist_id`

## Валидация безопасности
Перед формированием ссылки выполняются проверки:
- `client_bot_username` проходит regex-валидацию Telegram bot username.
- `specialist_id` должен быть валидным UUID (строка).

Если валидация не пройдена, внешняя ссылка не рендерится.
