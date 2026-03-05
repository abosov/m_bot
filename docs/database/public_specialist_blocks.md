# Таблица `specialist_public_block`

## Назначение
`specialist_public_block` хранит независимые текстовые блоки публичной страницы специалиста.

Раздельное хранение блоков позволяет:
- редактировать каждый блок отдельно;
- расширять список блоков без изменения базовой таблицы профиля;
- кэшировать блоки как самостоятельные сущности.

## Структура
Таблица создается SQL-миграцией `database/migrations/20260311_add_specialist_public_blocks.sql`.

```sql
CREATE TABLE specialist_public_block (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES specialist_public_profile(id) ON DELETE CASCADE,
    block_type TEXT NOT NULL,
    content TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 100,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(profile_id, block_type)
);
```

## Поддерживаемые типы блоков
- `about`
- `education`
- `documents`
- `services`
- `reviews`

Примечание: допустимые значения `block_type` должны валидироваться на backend до записи в БД.

## Ограничения
- Для одного профиля нельзя создать два блока одного типа.
  - Это обеспечивается ограничением `UNIQUE(profile_id, block_type)`.
- `content` обязателен (`NOT NULL`) и хранит текст блока.

## Пример хранения
Профиль `profile_id = 11111111-1111-1111-1111-111111111111` может иметь:
- блок `about` с `sort_order = 10`;
- блок `education` с `sort_order = 20`;
- блок `services` с `sort_order = 30`.

Повторная попытка вставки второго `about` для того же `profile_id` должна завершиться ошибкой уникальности.

## Безопасность
`content` должен проходить HTML-sanitization на backend перед рендером на публичной странице.
