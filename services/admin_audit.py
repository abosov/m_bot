from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AdminAuditLog
from services.log_context import log_event

logger = logging.getLogger(__name__)

_SECRET_KEYS = (
    "token",
    "password",
    "secret",
    "api_key",
    "authorization",
    "cookie",
)


def build_admin_audit_log_query(
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: UUID | None = None,
    success: bool | None = None,
) -> Select[tuple[AdminAuditLog]]:
    query = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc())

    if since is not None:
        query = query.where(AdminAuditLog.created_at >= since)

    if until is not None:
        query = query.where(AdminAuditLog.created_at <= until)

    if action is not None:
        query = query.where(AdminAuditLog.action == action)

    if target_type is not None:
        query = query.where(AdminAuditLog.target_type == target_type)

    if target_id is not None:
        query = query.where(AdminAuditLog.target_id == target_id)

    if success is not None:
        query = query.where(AdminAuditLog.success.is_(success))

    return query


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(secret_key in lowered for secret_key in _SECRET_KEYS)


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_secret_key(str(key)):
                sanitized[str(key)] = "[redacted]"
            else:
                sanitized[str(key)] = _sanitize_payload(item)
        return sanitized

    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]

    return value




def _is_forbidden_read_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in {"token", "tokens", "secret", "secrets", "refresh_token", "access_token"}
        or "token" in lowered
        or "secret" in lowered
    )


def sanitize_admin_audit_payload_for_ui(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_forbidden_read_key(str(key)):
                continue
            sanitized[str(key)] = sanitize_admin_audit_payload_for_ui(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_admin_audit_payload_for_ui(item) for item in value]

    return value


def _sanitize_error_message(error_message: str | None) -> str | None:
    if error_message is None:
        return None

    lowered = error_message.lower()
    if any(secret_key in lowered for secret_key in _SECRET_KEYS):
        return "[redacted]"

    return error_message[:500]


async def write_admin_audit_log(
    session: AsyncSession,
    *,
    request_id: str | None,
    admin_subject: str,
    action: str,
    target_type: str,
    target_id: UUID,
    success: bool,
    payload: dict,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Write immutable admin audit record.

    This helper is intentionally best-effort and must never break caller flow:
    any DB failure is swallowed with warning log event=admin_audit_log_failed.
    """

    try:
        sanitized_payload = _sanitize_payload(payload or {})
        sanitized_error_message = _sanitize_error_message(error_message)

        async with session.begin_nested():
            session.add(
                AdminAuditLog(
                    request_id=request_id,
                    admin_subject=admin_subject,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    success=success,
                    payload_json=sanitized_payload,
                    error_code=error_code,
                    error_message=sanitized_error_message,
                )
            )
            await session.flush()
    except Exception as exc:
        log_event(
            logger,
            logging.WARNING,
            event="admin_audit_log_failed",
            exception_class=exc.__class__.__name__,
            action=action,
            target_type=target_type,
            request_id=request_id,
        )
