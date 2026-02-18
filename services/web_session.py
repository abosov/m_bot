from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from typing import Any

import config


_DEFAULT_TTL_MINUTES = 60


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _resolve_signing_key() -> bytes:
    key_candidates = (
        getattr(config, "SECRET_KEY", None),
        os.getenv("SECRET_KEY"),
        config.ENCRYPTION_KEY,
        os.getenv("ENCRYPTION_KEY"),
        config.WEB_CONNECT_PEPPER,
    )

    for key in key_candidates:
        if key:
            return str(key).encode("utf-8")

    raise RuntimeError(
        "Missing signing key. Set SECRET_KEY or ENCRYPTION_KEY in environment."
    )


def _sign_payload(payload_b64: str, key: bytes) -> str:
    signature = hmac.new(key, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _base64url_encode(signature)


def sign_session_cookie(
    specialist_id: uuid.UUID | str,
    tg_user_id: int,
    ttl_minutes: int = _DEFAULT_TTL_MINUTES,
) -> str:
    if ttl_minutes <= 0:
        raise ValueError("ttl_minutes must be greater than zero")

    now = int(time.time())
    payload: dict[str, Any] = {
        "specialist_id": str(specialist_id),
        "tg_user_id": int(tg_user_id),
        "exp": now + (ttl_minutes * 60),
        "nonce": secrets.token_hex(4),
    }

    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _base64url_encode(payload_raw)

    key = _resolve_signing_key()
    signature = _sign_payload(payload_b64, key)
    return f"{payload_b64}.{signature}"


def verify_session_cookie(cookie_value: str) -> tuple[uuid.UUID, int] | None:
    if not cookie_value or "." not in cookie_value:
        return None

    payload_b64, signature = cookie_value.split(".", 1)
    try:
        key = _resolve_signing_key()
        expected_signature = _sign_payload(payload_b64, key)
        if not hmac.compare_digest(expected_signature, signature):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        specialist_id = uuid.UUID(str(payload["specialist_id"]))
        tg_user_id = int(payload["tg_user_id"])
        exp = int(payload["exp"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, base64.binascii.Error):
        return None

    if int(time.time()) >= exp:
        return None

    return specialist_id, tg_user_id
