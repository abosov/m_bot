# User Flow: Public Specialist Page

## URL routing
Публичная страница специалиста обрабатывается по короткому пути:
- `/{public_slug}`
- пример: `/TsarevaE_12`

Frontend route resolver:
1. Извлекает сегмент пути.
2. Проверяет slug по regex `^[A-Za-z]+[A-Za-z]_[1-9][0-9]$`.
3. Проверяет, что числовой суффикс в диапазоне `10..30`.
4. Проверяет, что slug не равен зарезервированным путям (`pricing`, `privacy`, `terms`, `revoke-access`, `api`, `static`, `assets`).

Если все проверки пройдены — открывается `specialist_profile_page`.
Иначе используется обычный роутинг сайта.

## Data flow
1. Пользователь открывает `/{public_slug}`.
2. Frontend направляет на `specialist_profile_page`.
3. Страница вызывает `GET /api/public/specialists/{slug}`.
4. Backend возвращает:
   - `profile`
   - `blocks`
   - `media`
   - `reviews`

## Security
- Применяется строгая валидация slug regex на уровне роутинга.
- Невалидный или зарезервированный path не должен интерпретироваться как публичная страница специалиста.
