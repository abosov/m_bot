from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import text

import config

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _hash_connect_token(raw_token: str) -> str:
    payload = f"{raw_token}{config.WEB_CONNECT_PEPPER}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def create_connect_token(
    db: "AsyncSession",
    specialist_id: uuid.UUID,
    tg_user_id: int,
    ttl_minutes: int = 15,
) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_connect_token(raw_token)

    await db.execute(
        text(
            """
            INSERT INTO web_connect_token (token_hash, specialist_id, tg_user_id, expires_at, used_at)
            VALUES (
                :token_hash,
                :specialist_id,
                :tg_user_id,
                now() + (:ttl_minutes * interval '1 minute'),
                NULL
            )
            """
        ),
        {
            "token_hash": token_hash,
            "specialist_id": specialist_id,
            "tg_user_id": tg_user_id,
            "ttl_minutes": ttl_minutes,
        },
    )
    await db.flush()
    return raw_token


async def consume_connect_token(
    db: "AsyncSession",
    raw_token: str,
) -> tuple[uuid.UUID, int] | None:
    token_hash = _hash_connect_token(raw_token)

    result = await db.execute(
        text(
            """
            UPDATE web_connect_token
            SET used_at = now()
            WHERE token_hash = :token_hash
              AND used_at IS NULL
              AND expires_at > now()
            RETURNING specialist_id, tg_user_id
            """
        ),
        {"token_hash": token_hash},
    )
    row = result.one_or_none()
    await db.flush()

    if row is None:
        return None

    specialist_id, tg_user_id = row
    return specialist_id, tg_user_id
