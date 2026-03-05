from __future__ import annotations

from typing import Any


async def get_public_specialist_by_slug(slug: str) -> dict[str, Any] | None:
    """Возвращает публичные данные специалиста по slug.

    Ожидаемый формат:
    {
      "profile": {..., "is_published": bool},
      "blocks": [...],
      "media": [...],
      "reviews": [...]
    }

    На данном этапе чтение из БД еще не подключено,
    поэтому возвращается None.
    """
    _ = slug
    return None
