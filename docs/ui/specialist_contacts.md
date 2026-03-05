# UI: Контакты специалиста

Под кнопкой `Связаться со специалистом` в Hero выводятся прямые контакты специалиста.

## Поля
- Telegram
- WhatsApp
- Телефон
- Email


## Источник данных
Поля берутся из `specialist_public_profile`:
- `contact_telegram`
- `contact_whatsapp`
- `contact_phone`
- `contact_email`

## Правило отображения
Показываются только непустые поля. Пустые/состоящие из пробелов значения не рендерятся.

## Безопасность
Email проходит basic validation по regex перед отображением.
Если email невалиден, поле `Email` не показывается.

## Реализация
- `frontend/components/specialist/Contacts.tsx`
- Использование в `frontend/components/specialist/Hero.tsx`
