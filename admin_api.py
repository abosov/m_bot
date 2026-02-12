from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

import config
from database import (
    BotHealthCheck,
    LogDirection,
    MessageLog,
    ServiceHeartbeat,
    async_session_factory,
)
from services.log_exporter import (
    parse_iso_datetime,
    serialize_bot_health_check,
    serialize_message_log,
    serialize_service_heartbeat,
)
from services.test_data_reset import TestDataResetError, execute_test_data_reset
from services.log_context import log_event
from services.request_context import get_request_id

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


class AdminTestDataResetRequest(BaseModel):
    names: list[str] = Field(default_factory=list)
    tg_user_ids: list[int] = Field(default_factory=list)
    dry_run: bool = True
    force: bool = False
    max_clients_threshold: int = 30


def require_admin_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not config.ADMIN_API_KEY:
        raise HTTPException(status_code=404, detail="Not found")
    if x_api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


def clamp_limit(value: int | None) -> int:
    if value is None:
        return 100
    return min(max(value, 1), 500)


def parse_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from exc


@router.get("/logs")
async def admin_logs(
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0),
    bot_id: int | None = Query(default=None),
    specialist_id: str | None = Query(default=None),
    tg_user_id: int | None = Query(default=None),
    direction: LogDirection | None = Query(default=None),
    is_error: bool | None = Query(default=None),
    redact: bool = Query(default=True),
    _auth: None = Depends(require_admin_key),
):
    request_id = get_request_id()
    since_dt = parse_iso_datetime(since) if since else None
    until_dt = parse_iso_datetime(until) if until else None
    limit_value = clamp_limit(limit)
    specialist_uuid = parse_uuid(specialist_id)

    log_event(
        logger,
        logging.INFO,
        event="admin_query",
        request_id=request_id,
        path="/admin/logs",
        tg_user_id=tg_user_id,
        is_error=is_error,
        created_at_since=since,
        created_at_until=until,
        limit=limit_value,
        offset=offset,
    )

    try:
        async with async_session_factory() as session:
            stmt = select(MessageLog)
            if since_dt:
                stmt = stmt.where(MessageLog.created_at >= since_dt)
            if until_dt:
                stmt = stmt.where(MessageLog.created_at <= until_dt)
            if bot_id is not None:
                stmt = stmt.where(MessageLog.bot_id == bot_id)
            if specialist_uuid is not None:
                stmt = stmt.where(MessageLog.specialist_id == specialist_uuid)
            if tg_user_id is not None:
                stmt = stmt.where(MessageLog.tg_user_id == tg_user_id)
            if direction is not None:
                stmt = stmt.where(MessageLog.direction == direction)
            if is_error is not None:
                stmt = stmt.where(MessageLog.is_error == is_error)
            stmt = stmt.order_by(MessageLog.created_at.asc())
            stmt = stmt.limit(limit_value).offset(offset)
            result = await session.execute(stmt)
            if config.APP_ENV == "prod" and not redact:
                raise HTTPException(status_code=403, detail="Unredacted logs are disabled in production")
            items = [serialize_message_log(row, redact=redact) for row in result.scalars().all()]
    except Exception:
        logger.exception("admin_logs failed request_id=%s", request_id)
        raise

    return {"items": items, "limit": limit_value, "offset": offset}


@router.get("/heartbeats")
async def admin_heartbeats(
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0),
    service_name: str | None = Query(default=None),
    _auth: None = Depends(require_admin_key),
):
    since_dt = parse_iso_datetime(since) if since else None
    until_dt = parse_iso_datetime(until) if until else None
    limit_value = clamp_limit(limit)

    async with async_session_factory() as session:
        stmt = select(ServiceHeartbeat)
        if since_dt:
            stmt = stmt.where(ServiceHeartbeat.ts >= since_dt)
        if until_dt:
            stmt = stmt.where(ServiceHeartbeat.ts <= until_dt)
        if service_name:
            stmt = stmt.where(ServiceHeartbeat.service_name == service_name)
        stmt = stmt.order_by(ServiceHeartbeat.ts.asc())
        stmt = stmt.limit(limit_value).offset(offset)
        result = await session.execute(stmt)
        items = [serialize_service_heartbeat(row) for row in result.scalars().all()]

    return {"items": items, "limit": limit_value, "offset": offset}


@router.get("/bot-health-checks")
async def admin_bot_health_checks(
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0),
    specialist_id: str | None = Query(default=None),
    bot_id: int | None = Query(default=None),
    _auth: None = Depends(require_admin_key),
):
    since_dt = parse_iso_datetime(since) if since else None
    until_dt = parse_iso_datetime(until) if until else None
    limit_value = clamp_limit(limit)
    specialist_uuid = parse_uuid(specialist_id)

    async with async_session_factory() as session:
        stmt = select(BotHealthCheck)
        if since_dt:
            stmt = stmt.where(BotHealthCheck.checked_at >= since_dt)
        if until_dt:
            stmt = stmt.where(BotHealthCheck.checked_at <= until_dt)
        if specialist_uuid is not None:
            stmt = stmt.where(BotHealthCheck.specialist_id == specialist_uuid)
        if bot_id is not None:
            stmt = stmt.where(BotHealthCheck.bot_user_id == bot_id)
        stmt = stmt.order_by(BotHealthCheck.checked_at.asc())
        stmt = stmt.limit(limit_value).offset(offset)
        result = await session.execute(stmt)
        items = [serialize_bot_health_check(row) for row in result.scalars().all()]

    return {"items": items, "limit": limit_value, "offset": offset}


@router.post("/test-data/reset")
async def admin_test_data_reset(
    payload: AdminTestDataResetRequest,
    _auth: None = Depends(require_admin_key),
):
    try:
        return await execute_test_data_reset(
            session_factory=async_session_factory,
            names=payload.names or None,
            tg_user_ids=payload.tg_user_ids or None,
            dry_run=payload.dry_run,
            force=payload.force,
            max_clients_threshold=payload.max_clients_threshold,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TestDataResetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
