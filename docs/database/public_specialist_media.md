# Таблица `specialist_public_media`

## Назначение
`specialist_public_media` хранит медиа-объекты публичной страницы специалиста:
- фотографии;
- сканы дипломов и сертификатов (документы).

Таблица хранит только метаданные и ключ файла, а не бинарные файлы.

## Структура
Таблица создается SQL-миграцией `database/migrations/20260312_add_specialist_public_media.sql`.

```sql
CREATE TABLE specialist_public_media (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES specialist_public_profile(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'document')),
    file_key TEXT NOT NULL,
    title TEXT,
    sort_order INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## Назначение колонок
- `id` — идентификатор медиа-записи.
- `profile_id` — ссылка на публичный профиль (`specialist_public_profile.id`), удаляется каскадно.
- `media_type` — тип медиа (`photo` или `document`).
- `file_key` — ключ файла в файловом/объектном хранилище.
- `title` — заголовок/подпись медиа (опционально).
- `sort_order` — порядок отображения (по умолчанию `100`).
- `created_at` — дата создания записи.

## Правила
- Допустимые значения `media_type`: `photo`, `document`.
- Файлы не хранятся в базе; в базе хранится только `file_key`.

## Безопасность
- Запрещено отдавать `file_key` напрямую во внешний контур без проверки прав и контекста публикации.
- Для выдачи клиенту следует использовать проверенный backend-эндпоинт/подписанные URL после валидации доступа.
