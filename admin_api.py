from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Text, cast, func, select

import config
from database import (
    BotHealthCheck,
    Client,
    LogDirection,
    MessageLog,
    ServiceHeartbeat,
    Specialist,
    SpecialistAuthTelegram,
    SpecialistProfile,
    SpecialistStatus,
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




async def build_admin_specialists_payload(
    *,
    limit: int | None = 100,
    offset: int = 0,
    status: SpecialistStatus | None = None,
    include_system: bool = False,
) -> dict[str, object]:
    limit_value = clamp_limit(limit)

    clients_count_subquery = (
        select(
            Client.specialist_id.label("specialist_id"),
            func.count(Client.client_id).label("clients_count"),
        )
        .group_by(Client.specialist_id)
        .subquery()
    )

    last_activity_subquery = (
        select(
            MessageLog.specialist_id.label("specialist_id"),
            func.max(MessageLog.created_at).label("last_activity_at"),
        )
        .where(MessageLog.specialist_id.is_not(None))
        .group_by(MessageLog.specialist_id)
        .subquery()
    )

    async with async_session_factory() as session:
        total_stmt = select(func.count()).select_from(Specialist)
        if status is not None:
            total_stmt = total_stmt.where(Specialist.status == status)
        if not include_system:
            total_stmt = total_stmt.where(Specialist.is_system.is_(False))

        stmt = (
            select(
                Specialist.specialist_id,
                func.coalesce(
                    SpecialistProfile.public_name,
                    SpecialistAuthTelegram.tg_username,
                    SpecialistAuthTelegram.tg_first_name,
                    cast(Specialist.specialist_id, Text),
                ).label("public_name"),
                Specialist.status,
                Specialist.created_at,
                SpecialistProfile.tariff_plan,
                func.coalesce(clients_count_subquery.c.clients_count, 0).label("clients_count"),
                last_activity_subquery.c.last_activity_at,
            )
            .outerjoin(SpecialistProfile, SpecialistProfile.specialist_id == Specialist.specialist_id)
            .outerjoin(
                SpecialistAuthTelegram,
                SpecialistAuthTelegram.specialist_id == Specialist.specialist_id,
            )
            .outerjoin(clients_count_subquery, clients_count_subquery.c.specialist_id == Specialist.specialist_id)
            .outerjoin(last_activity_subquery, last_activity_subquery.c.specialist_id == Specialist.specialist_id)
        )
        if status is not None:
            stmt = stmt.where(Specialist.status == status)
        if not include_system:
            stmt = stmt.where(Specialist.is_system.is_(False))

        stmt = stmt.order_by(Specialist.created_at.desc()).limit(limit_value).offset(offset)
        rows = (await session.execute(stmt)).all()
        total = int((await session.execute(total_stmt)).scalar_one())

    items = [
        {
            "specialist_id": str(row.specialist_id),
            "public_name": row.public_name,
            "status": row.status.value if row.status is not None else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tariff_plan": row.tariff_plan.value if row.tariff_plan is not None else None,
            "clients_count": int(row.clients_count or 0),
            "last_activity_at": row.last_activity_at.isoformat() if row.last_activity_at else None,
        }
        for row in rows
    ]

    return {"items": items, "limit": limit_value, "offset": offset, "total": total}


async def compute_admin_overview(session, include_system: bool = False) -> dict[str, object]:
    now_utc = datetime.now(timezone.utc)
    active_since_utc = now_utc - timedelta(days=7)

    specialists_total_stmt = select(func.count()).select_from(Specialist)
    if not include_system:
        specialists_total_stmt = specialists_total_stmt.where(Specialist.is_system.is_(False))
    specialists_total = int((await session.execute(specialists_total_stmt)).scalar_one())

    clients_total_stmt = select(func.count()).select_from(Client)
    if not include_system:
        clients_total_stmt = clients_total_stmt.join(Specialist, Specialist.specialist_id == Client.specialist_id).where(
            Specialist.is_system.is_(False)
        )
    clients_total = int((await session.execute(clients_total_stmt)).scalar_one())

    last_activity_subquery = (
        select(
            MessageLog.specialist_id.label("specialist_id"),
            func.max(MessageLog.created_at).label("last_activity_at"),
        )
        .where(MessageLog.specialist_id.is_not(None))
        .group_by(MessageLog.specialist_id)
        .subquery()
    )
    specialists_active_stmt = (
        select(func.count())
        .select_from(last_activity_subquery)
        .join(Specialist, Specialist.specialist_id == last_activity_subquery.c.specialist_id)
        .where(last_activity_subquery.c.last_activity_at >= active_since_utc)
    )
    if not include_system:
        specialists_active_stmt = specialists_active_stmt.where(Specialist.is_system.is_(False))

    specialists_active_7d = int((await session.execute(specialists_active_stmt)).scalar_one())

    return {
        "specialists_total": specialists_total,
        "clients_total": clients_total,
        "specialists_active_7d": specialists_active_7d,
        "errors_24h": 0,
        "computed_at_utc": now_utc.isoformat(),
    }


@router.get("/specialists")
async def admin_specialists(
    limit: int | None = Query(default=100),
    offset: int = Query(default=0),
    status: SpecialistStatus | None = Query(default=None),
    include_system: bool = Query(default=False),
    _auth: None = Depends(require_admin_key),
):
    return await build_admin_specialists_payload(
        limit=limit,
        offset=offset,
        status=status,
        include_system=include_system,
    )


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
