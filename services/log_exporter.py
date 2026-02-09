from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import Select, select

from database import (
    BotHealthCheck,
    LogDirection,
    MessageLog,
    ServiceHeartbeat,
    async_session_factory,
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d)[\d\s().-]{7,}\d)")
TOKEN_RE = re.compile(r"[A-Za-z0-9+/_=-]{32,}")
HEX_RE = re.compile(r"\b[a-fA-F0-9]{32,}\b")


def parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def normalize_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_error_summary(error_details: str | None, max_len: int = 200) -> str | None:
    if not error_details:
        return None
    first_line = error_details.strip().splitlines()[0]
    if len(first_line) <= max_len:
        return first_line
    return first_line[: max_len - 1] + "…"


def redact_content(content: str | None) -> str | None:
    if content is None:
        return None
    if HEX_RE.search(content) or TOKEN_RE.search(content):
        return "[REDACTED]"
    content = EMAIL_RE.sub("[REDACTED_EMAIL]", content)
    content = PHONE_RE.sub("[REDACTED_PHONE]", content)
    return content


def apply_time_filters(
    stmt: Select,
    column,
    since: datetime | None,
    until: datetime | None,
) -> Select:
    if since is not None:
        stmt = stmt.where(column >= since)
    if until is not None:
        stmt = stmt.where(column <= until)
    return stmt


def serialize_message_log(log: MessageLog, redact: bool) -> dict:
    content = log.content
    if redact:
        content = redact_content(content)
    error_details = log.error_details
    if redact:
        error_details = redact_content(error_details)
    return {
        "timestamp": normalize_timestamp(log.created_at),
        "source": "message_log",
        "bot_id": log.bot_id,
        "specialist_id": str(log.specialist_id) if log.specialist_id else None,
        "tg_user_id": log.tg_user_id,
        "direction": log.direction.value,
        "fsm_state": log.fsm_state,
        "handler_name": log.handler_name,
        "processing_time": log.processing_time,
        "is_error": log.is_error,
        "error_summary": build_error_summary(log.error_details),
        "error_details": error_details,
        "content": content,
    }


def serialize_service_heartbeat(heartbeat: ServiceHeartbeat) -> dict:
    return {
        "timestamp": normalize_timestamp(heartbeat.ts),
        "source": "service_heartbeat",
        "service_name": heartbeat.service_name,
        "db_ok": heartbeat.db_ok,
        "loop_ok": heartbeat.loop_ok,
        "latency_ms": heartbeat.latency_ms,
        "details": heartbeat.details,
    }


def serialize_bot_health_check(check: BotHealthCheck) -> dict:
    return {
        "timestamp": normalize_timestamp(check.checked_at),
        "source": "bot_health_check",
        "specialist_id": str(check.specialist_id),
        "bot_id": check.bot_user_id,
        "status": check.status.value,
        "latency_ms": check.latency_ms,
        "error_details": check.error_details,
    }


async def collect_logs(
    source: str,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int | None = None,
    bot_id: int | None = None,
    specialist_id: uuid.UUID | None = None,
    tg_user_id: int | None = None,
    direction: LogDirection | None = None,
    is_error: bool | None = None,
    redact: bool = False,
) -> list[dict]:
    async with async_session_factory() as session:
        if source == "message_logs":
            stmt = select(MessageLog)
            stmt = apply_time_filters(stmt, MessageLog.created_at, since, until)
            if bot_id is not None:
                stmt = stmt.where(MessageLog.bot_id == bot_id)
            if specialist_id is not None:
                stmt = stmt.where(MessageLog.specialist_id == specialist_id)
            if tg_user_id is not None:
                stmt = stmt.where(MessageLog.tg_user_id == tg_user_id)
            if direction is not None:
                stmt = stmt.where(MessageLog.direction == direction)
            if is_error is not None:
                stmt = stmt.where(MessageLog.is_error == is_error)
            stmt = stmt.order_by(MessageLog.created_at.asc())
            if limit:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [serialize_message_log(row, redact) for row in result.scalars().all()]

        if source == "service_heartbeats":
            stmt = select(ServiceHeartbeat)
            stmt = apply_time_filters(stmt, ServiceHeartbeat.ts, since, until)
            stmt = stmt.order_by(ServiceHeartbeat.ts.asc())
            if limit:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [serialize_service_heartbeat(row) for row in result.scalars().all()]

        if source == "bot_health_checks":
            stmt = select(BotHealthCheck)
            stmt = apply_time_filters(stmt, BotHealthCheck.checked_at, since, until)
            if bot_id is not None:
                stmt = stmt.where(BotHealthCheck.bot_user_id == bot_id)
            if specialist_id is not None:
                stmt = stmt.where(BotHealthCheck.specialist_id == specialist_id)
            stmt = stmt.order_by(BotHealthCheck.checked_at.asc())
            if limit:
                stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return [serialize_bot_health_check(row) for row in result.scalars().all()]

        raise ValueError(f"Unsupported source: {source}")


def render_jsonl(records: Iterable[dict]) -> str:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    return "\n".join(lines) + ("\n" if lines else "")


def render_message_logs_csv(records: Sequence[dict]) -> str:
    import csv
    import io

    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "source",
        "bot_id",
        "specialist_id",
        "tg_user_id",
        "direction",
        "fsm_state",
        "handler_name",
        "processing_time",
        "is_error",
        "error_summary",
        "error_details",
        "content",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow({name: record.get(name) for name in fieldnames})
    return output.getvalue()
