# Таблица `specialist_public_profile`

## Назначение
`specialist_public_profile` хранит публичные данные специалиста для мини-лендинга и отделяет их от основной сущности `specialist`.

Это позволяет:
- не смешивать внутренние и публичные данные;
- безопасно расширять публичный профиль независимо от внутренних полей специалиста.

## Схема
Таблица создается SQL-миграцией `database/migrations/20260310_add_specialist_public_profile.sql`.

```sql
CREATE TABLE specialist_public_profile (
    id UUID PRIMARY KEY,
    specialist_id UUID NOT NULL REFERENCES specialist(specialist_id) ON DELETE CASCADE,
    public_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    specialization TEXT NOT NULL,
    hero_quote TEXT,
    contact_telegram TEXT,
    contact_whatsapp TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    client_bot_username TEXT NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_specialist_public_slug
ON specialist_public_profile(public_slug);
```

## Описание колонок
- `id` — первичный ключ записи публичного профиля.
- `specialist_id` — ссылка на специалиста (`specialist.specialist_id`), удаляется каскадно при удалении специалиста.
- `public_slug` — уникальный slug публичной страницы (обязательное поле).
- `display_name` — отображаемое имя специалиста на публичной странице (совместимость публичного рендера).
- `first_name` — структурное имя специалиста для приватного редактирования.
- `middle_name` — структурное отчество/среднее имя (опционально).
- `last_name` — структурная фамилия специалиста.
- `specialization` — специализация специалиста.
- `hero_quote` — цитата/слоган в hero-блоке (опционально).
- `contact_telegram` — контакт Telegram (опционально).
- `contact_whatsapp` — контакт WhatsApp (опционально).
- `contact_phone` — контактный телефон (опционально).
- `contact_email` — контактный email (опционально).
- `client_bot_username` — username Telegram-бота для записи (обязательное поле).
- `is_published` — признак публикации страницы (`FALSE` по умолчанию).
- `created_at` — дата создания записи.
- `updated_at` — дата последнего обновления записи.

## Ограничения и безопасность
- `public_slug` обязан быть заполнен (`NOT NULL`).
- `public_slug` уникален (`UNIQUE` + отдельный уникальный индекс `idx_specialist_public_slug`).
- Валидация формата slug выполняется на backend **до** записи в БД.


## Нормализация ФИО
- Новые колонки `first_name`/`middle_name`/`last_name` являются source of truth для приватного API редактирования профиля.
- `display_name` сохраняется и продолжает использоваться публичной страницей для обратной совместимости.
- При сохранении через приватный API `display_name` пересчитывается из name-parts.
