# Public Specialist API

## Endpoint
`GET /api/public/specialists/{slug}`

Возвращает данные публичной страницы специалиста для frontend-лендинга.

## Валидация
Перед чтением данных API:
1. проверяет формат `slug` по regex `^[A-Za-z]+[A-Za-z]_[1-9][0-9]$`;
2. проверяет диапазон числового суффикса `10..30`;
3. отклоняет зарезервированные значения (`pricing`, `privacy`, `terms`, `revoke-access`, `api`, `static`, `assets`).

При невалидном slug возвращается `400 invalid_slug`.

## Поведение
- Если профиль не найден: `404 not_found`.
- Если профиль найден, но `is_published = false`: `404 not_found`.
- Если профиль опубликован: `200 OK`.

## Response JSON
```json
{
  "profile": {},
  "blocks": [],
  "media": [],
  "reviews": []
}
```

Гарантия безопасности:
- endpoint возвращает только публичные поля `profile`;
- private-поля внутренней сущности `specialist` не должны попадать в ответ.
