from __future__ import annotations

import uuid
import re
import unicodedata
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import Specialist, SpecialistProfile, TelegramBot

_BLOCK_SORT_ORDER = {
    "about": 10,
    "education": 20,
    "services": 30,
    "reviews": 40,
}

_MAX_SPECIALIZATION_LEN = 200
_MAX_HERO_QUOTE_LEN = 200
_MAX_BLOCK_LEN = 8000
_MAX_DISPLAY_NAME_LEN = 200
_SLUG_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9]+")
_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _validate_profile_payload(*, specialization: str, hero_quote: str, about: str, education: str, services: str, reviews: str) -> None:
    if not specialization:
        raise ValueError("specialization_required")
    if len(specialization) > _MAX_SPECIALIZATION_LEN:
        raise ValueError("specialization_too_long")
    if len(hero_quote) > _MAX_HERO_QUOTE_LEN:
        raise ValueError("hero_quote_too_long")

    for block_value in (about, education, services, reviews):
        if len(block_value) > _MAX_BLOCK_LEN:
            raise ValueError("block_too_long")


def split_display_name(display_name: str) -> tuple[str, str, str]:
    normalized = " ".join((display_name or "").split())
    if not normalized:
        return "", "", ""

    tokens = normalized.split(" ")
    if len(tokens) == 1:
        return tokens[0], "", ""

    first_name = tokens[0]
    last_name = tokens[-1]
    middle_name = " ".join(tokens[1:-1])
    return first_name, middle_name, last_name


def build_display_name(first_name: str, middle_name: str, last_name: str) -> str:
    return " ".join(part.strip() for part in (first_name, middle_name, last_name) if part and part.strip())


def _normalize_name_part(value: str | None) -> str:
    return _normalize_text(value)


def _latinize_to_slug_base(value: str) -> str:
    text_value = " ".join((value or "").split()).lower()
    if not text_value:
        return ""

    transliterated = "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text_value)
    normalized = unicodedata.normalize("NFKD", transliterated)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    compact = _SLUG_SAFE_CHARS_RE.sub("", ascii_only)
    if not compact:
        return ""

    starts_with_alpha_index = next((idx for idx, ch in enumerate(compact) if ch.isalpha()), None)
    if starts_with_alpha_index is None:
        return ""
    return compact[starts_with_alpha_index:]


async def _generate_public_slug_for_profile(
    session: AsyncSession,
    *,
    profile_id,
    first_name: str,
    last_name: str,
    display_name: str,
) -> str:
    name_source = f"{first_name} {last_name}".strip() if (first_name or last_name) else display_name
    base = _latinize_to_slug_base(name_source) or "specialist"

    existing = (
        await session.execute(
            text(
                """
                SELECT public_slug
                FROM specialist_public_profile
                WHERE public_slug LIKE :prefix
                  AND id != :profile_id
                """
            ),
            {"prefix": f"{base}_%", "profile_id": profile_id},
        )
    ).scalars().all()

    occupied_suffixes: set[int] = set()
    for slug in existing:
        slug_str = str(slug or "").strip()
        if not slug_str.startswith(f"{base}_"):
            continue
        suffix_raw = slug_str.rsplit("_", maxsplit=1)[-1]
        if len(suffix_raw) != 2 or not suffix_raw.isdigit():
            continue
        occupied_suffixes.add(int(suffix_raw))

    for suffix in range(10, 31):
        if suffix not in occupied_suffixes:
            return f"{base}_{suffix:02d}"

    raise ValueError("slug_generation_failed")


async def _resolve_client_bot_username(session: AsyncSession, specialist_id) -> str:
    bot_username = (
        await session.execute(
            select(TelegramBot.bot_username)
            .where(TelegramBot.specialist_id == specialist_id)
            .order_by(TelegramBot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return (bot_username or "").strip()


async def get_or_create_public_profile_for_specialist(session: AsyncSession, specialist_id) -> dict:
    sid_text = str(specialist_id)
    row = (
        await session.execute(
            text("SELECT * FROM specialist_public_profile WHERE specialist_id = :sid LIMIT 1"),
            {"sid": sid_text},
        )
    ).mappings().first()
    if row is not None:
        return dict(row)

    specialist = await session.get(Specialist, specialist_id)
    specialist_profile = await session.get(SpecialistProfile, specialist_id)

    display_name = ""
    if specialist_profile is not None and specialist_profile.public_name:
        display_name = specialist_profile.public_name.strip()

    fallback_first_name, fallback_middle_name, fallback_last_name = split_display_name(display_name)
    specialization = (getattr(specialist, "specialization", None) or "").strip() if specialist is not None else ""
    client_bot_username = await _resolve_client_bot_username(session, specialist_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    profile_id = str(uuid.uuid4())

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_profile
                (id, specialist_id, public_slug, display_name, first_name, middle_name, last_name, specialization, hero_quote,
                 contact_telegram, contact_whatsapp, contact_phone, contact_email,
                 client_bot_username, is_published, created_at, updated_at)
            VALUES
                (:id, :specialist_id, :public_slug, :display_name, :first_name, :middle_name, :last_name, :specialization, :hero_quote,
                 :contact_telegram, :contact_whatsapp, :contact_phone, :contact_email,
                 :client_bot_username, :is_published, :created_at, :updated_at)
            """
        ),
        {
            "id": profile_id,
            "specialist_id": sid_text,
            "public_slug": "",
            "display_name": display_name,
            "first_name": fallback_first_name or None,
            "middle_name": fallback_middle_name or None,
            "last_name": fallback_last_name or None,
            "specialization": specialization,
            "hero_quote": "",
            "contact_telegram": None,
            "contact_whatsapp": None,
            "contact_phone": None,
            "contact_email": None,
            "client_bot_username": client_bot_username,
            "is_published": False,
            "created_at": now,
            "updated_at": now,
        },
    )
    return {
        "id": profile_id,
        "specialist_id": specialist_id,
        "display_name": display_name,
        "first_name": fallback_first_name or None,
        "middle_name": fallback_middle_name or None,
        "last_name": fallback_last_name or None,
        "specialization": specialization,
        "hero_quote": "",
        "public_slug": "",
    }


async def _get_blocks_by_type(session: AsyncSession, profile_id) -> dict[str, dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT profile_id, block_type, content, sort_order, updated_at
                FROM specialist_public_block
                WHERE profile_id = :profile_id
                  AND block_type IN ('about', 'education', 'services', 'reviews')
                """
            ),
            {"profile_id": profile_id},
        )
    ).mappings().all()
    return {row["block_type"]: dict(row) for row in rows}


async def read_specialist_profile_draft(session: AsyncSession, specialist_id) -> dict[str, str | bool | None]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    blocks_by_type = await _get_blocks_by_type(session, profile["id"])

    first_name_raw = profile.get("first_name")
    middle_name_raw = profile.get("middle_name")
    last_name_raw = profile.get("last_name")

    if first_name_raw is None and middle_name_raw is None and last_name_raw is None:
        first_name, middle_name, last_name = split_display_name(profile.get("display_name") or "")
    else:
        first_name = _normalize_name_part(first_name_raw)
        middle_name = _normalize_name_part(middle_name_raw)
        last_name = _normalize_name_part(last_name_raw)

    return {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "specialization": (profile.get("specialization") or "").strip(),
        "hero_quote": (profile.get("hero_quote") or "").strip(),
        "about": (blocks_by_type.get("about", {}).get("content") or "").strip(),
        "education": (blocks_by_type.get("education", {}).get("content") or "").strip(),
        "services": (blocks_by_type.get("services", {}).get("content") or "").strip(),
        "reviews": (blocks_by_type.get("reviews", {}).get("content") or "").strip(),
        "public_slug": ((profile.get("public_slug") or "").strip() or None),
        "is_published": bool(profile.get("is_published", False)),
    }


async def update_specialist_profile_draft(
    session: AsyncSession,
    *,
    specialist_id,
    first_name: str,
    middle_name: str,
    last_name: str,
    specialization: str,
    hero_quote: str,
    about: str,
    education: str,
    services: str,
    reviews: str,
) -> dict[str, str]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)

    normalized_first_name = _normalize_text(first_name)
    normalized_middle_name = _normalize_text(middle_name)
    normalized_last_name = _normalize_text(last_name)
    normalized_specialization = _normalize_text(specialization)
    normalized_hero_quote = _normalize_text(hero_quote)
    normalized_about = _normalize_text(about)
    normalized_education = _normalize_text(education)
    normalized_services = _normalize_text(services)
    normalized_reviews = _normalize_text(reviews)

    _validate_profile_payload(
        specialization=normalized_specialization,
        hero_quote=normalized_hero_quote,
        about=normalized_about,
        education=normalized_education,
        services=normalized_services,
        reviews=normalized_reviews,
    )

    display_name = build_display_name(normalized_first_name, normalized_middle_name, normalized_last_name)
    if len(display_name) > _MAX_DISPLAY_NAME_LEN:
        raise ValueError("display_name_too_long")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    current_slug = (profile.get("public_slug") or "").strip()
    if not current_slug:
        current_slug = await _generate_public_slug_for_profile(
            session,
            profile_id=profile["id"],
            first_name=normalized_first_name,
            last_name=normalized_last_name,
            display_name=display_name,
        )

    await session.execute(
        text(
            """
            UPDATE specialist_public_profile
               SET display_name = :display_name,
                   first_name = :first_name,
                   middle_name = :middle_name,
                   last_name = :last_name,
                   specialization = :specialization,
                   hero_quote = :hero_quote,
                   public_slug = COALESCE(NULLIF(public_slug, ''), :public_slug),
                   updated_at = :updated_at
             WHERE id = :id
            """
        ),
        {
            "id": profile["id"],
            "display_name": display_name,
            "first_name": normalized_first_name or None,
            "middle_name": normalized_middle_name or None,
            "last_name": normalized_last_name or None,
            "specialization": normalized_specialization,
            "hero_quote": normalized_hero_quote or None,
            "public_slug": current_slug,
            "updated_at": now,
        },
    )

    payload = {
        "about": normalized_about,
        "education": normalized_education,
        "services": normalized_services,
        "reviews": normalized_reviews,
    }
    blocks_by_type = await _get_blocks_by_type(session, profile["id"])
    for block_type, content in payload.items():
        current = blocks_by_type.get(block_type)
        if current is None:
            await session.execute(
                text(
                    """
                    INSERT INTO specialist_public_block
                        (id, profile_id, block_type, content, sort_order, updated_at)
                    VALUES
                        (:id, :profile_id, :block_type, :content, :sort_order, :updated_at)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "profile_id": profile["id"],
                    "block_type": block_type,
                    "content": content,
                    "sort_order": _BLOCK_SORT_ORDER[block_type],
                    "updated_at": now,
                },
            )
            continue

        await session.execute(
            text(
                """
                UPDATE specialist_public_block
                   SET content = :content,
                       updated_at = :updated_at
                 WHERE profile_id = :profile_id
                   AND block_type = :block_type
                """
            ),
            {
                "profile_id": profile["id"],
                "block_type": block_type,
                "content": content,
                "updated_at": now,
            },
        )

    return await read_specialist_profile_draft(session, specialist_id)


async def publish_specialist_profile(session: AsyncSession, *, specialist_id) -> dict[str, bool]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    public_slug = (profile.get("public_slug") or "").strip()
    if not public_slug:
        raise ValueError("slug_missing")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.execute(
        text(
            """
            UPDATE specialist_public_profile
               SET is_published = :is_published,
                   updated_at = :updated_at
             WHERE id = :id
            """
        ),
        {
            "id": profile["id"],
            "is_published": True,
            "updated_at": now,
        },
    )
    return {"ok": True, "is_published": True}


async def unpublish_specialist_profile(session: AsyncSession, *, specialist_id) -> dict[str, bool]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.execute(
        text(
            """
            UPDATE specialist_public_profile
               SET is_published = :is_published,
                   updated_at = :updated_at
             WHERE id = :id
            """
        ),
        {
            "id": profile["id"],
            "is_published": False,
            "updated_at": now,
        },
    )
    return {"ok": True, "is_published": False}


async def replace_specialist_profile_photo(
    session: AsyncSession,
    *,
    specialist_id,
    file_key: str,
    title: str,
) -> list[str]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    old_photo_keys = (
        await session.execute(
            text(
                """
                SELECT file_key
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                  AND media_type = 'photo'
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).scalars().all()

    await session.execute(
        text(
            """
            DELETE FROM specialist_public_media
            WHERE profile_id = :profile_id
              AND media_type = 'photo'
            """
        ),
        {"profile_id": profile["id"]},
    )

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_media
                (id, profile_id, media_type, file_key, title, sort_order, created_at)
            VALUES
                (:id, :profile_id, :media_type, :file_key, :title, :sort_order, :created_at)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "profile_id": profile["id"],
            "media_type": "photo",
            "file_key": file_key,
            "title": title,
            "sort_order": 10,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    return [str(key) for key in old_photo_keys if key]


async def add_specialist_profile_document(
    session: AsyncSession,
    *,
    specialist_id,
    file_key: str,
    title: str,
) -> None:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    current_max_sort = (
        await session.execute(
            text(
                """
                SELECT MAX(sort_order)
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                  AND media_type = 'document'
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).scalar_one_or_none()
    next_sort = max(100, int(current_max_sort or 99) + 1)

    await session.execute(
        text(
            """
            INSERT INTO specialist_public_media
                (id, profile_id, media_type, file_key, title, sort_order, created_at)
            VALUES
                (:id, :profile_id, :media_type, :file_key, :title, :sort_order, :created_at)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "profile_id": profile["id"],
            "media_type": "document",
            "file_key": file_key,
            "title": title,
            "sort_order": next_sort,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )


async def list_specialist_profile_media(session: AsyncSession, *, specialist_id) -> list[dict]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    rows = (
        await session.execute(
            text(
                """
                SELECT id, media_type, file_key, title, sort_order, created_at
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                ORDER BY sort_order ASC, created_at ASC
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).mappings().all()
    return [
        {
            "id": str(row["id"]),
            "media_type": str(row["media_type"]),
            "file_key": str(row["file_key"] or "") if str(row["media_type"]) == "photo" else None,
            "title": str(row["title"] or ""),
            "sort_order": int(row["sort_order"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


async def delete_specialist_profile_photo(session: AsyncSession, *, specialist_id) -> list[str]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    keys = (
        await session.execute(
            text(
                """
                SELECT file_key
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                  AND media_type = 'photo'
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).scalars().all()

    await session.execute(
        text(
            """
            DELETE FROM specialist_public_media
            WHERE profile_id = :profile_id
              AND media_type = 'photo'
            """
        ),
        {"profile_id": profile["id"]},
    )

    return [str(key) for key in keys if key]


async def list_specialist_media_file_keys(session: AsyncSession, *, specialist_id) -> list[str]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    rows = (
        await session.execute(
            text(
                """
                SELECT file_key
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).scalars().all()
    return [str(row) for row in rows if row]


async def delete_specialist_profile_media(session: AsyncSession, *, specialist_id) -> list[str]:
    profile = await get_or_create_public_profile_for_specialist(session, specialist_id)
    keys = (
        await session.execute(
            text(
                """
                SELECT file_key
                FROM specialist_public_media
                WHERE profile_id = :profile_id
                """
            ),
            {"profile_id": profile["id"]},
        )
    ).scalars().all()

    await session.execute(
        text(
            """
            DELETE FROM specialist_public_media
            WHERE profile_id = :profile_id
            """
        ),
        {"profile_id": profile["id"]},
    )
    return [str(key) for key in keys if key]
