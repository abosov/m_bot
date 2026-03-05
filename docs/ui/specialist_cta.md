# UI: Финальная CTA кнопка "Записаться на консультацию"

Компонент: `frontend/components/specialist/SectionCTA.tsx`.

## Цель
Главный конверсионный элемент внизу страницы — большая кнопка записи на консультацию.

## Формат ссылки
`https://t.me/{client_bot_username}?start=book_{specialist_id}`

## Источник данных
Из `specialist_public_profile`:
- `client_bot_username`
- `specialist_id`

## Безопасность
Перед формированием ссылки выполняется валидация:
- `client_bot_username` должен соответствовать regex для Telegram bot username;
- `specialist_id` должен быть валидным UUID (строка).

Если данные невалидны, CTA-секция не рендерится.
