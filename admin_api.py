from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
from sqlalchemy import Text, and_, cast, desc, exists, func, select

import config
from database import (
    BotHealthCheck,
    Client,
    LogDirection,
    MessageLog,
    ServiceHeartbeat,
    Specialist,
    GoogleOAuth,
    GoogleOAuthStatus,
    SpecialistAuthTelegram,
    SpecialistCalendarSettings,
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
from services import admin_ui_session
from services.log_context import log_event
from services.request_context import get_request_id

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

ADMIN_UI_COOKIE_NAME = "admin_session"


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
    oauth_missing: bool = False,
    calendar_missing: bool = False,
    inactive_days_gt: int | None = None,
) -> dict[str, object]:
    limit_value = clamp_limit(limit)
    now_utc = datetime.now(timezone.utc)
    active_since_utc = now_utc - timedelta(days=7)

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

    oauth_connected_exists = exists(
        select(1)
        .select_from(GoogleOAuth)
        .where(
            and_(
                GoogleOAuth.specialist_id == Specialist.specialist_id,
                GoogleOAuth.refresh_token_encrypted != "",
                GoogleOAuth.status == GoogleOAuthStatus.connected,
            )
        )
    )

    calendar_selected_exists = exists(
        select(1)
        .select_from(SpecialistCalendarSettings)
        .where(
            and_(
                SpecialistCalendarSettings.specialist_id == Specialist.specialist_id,
                SpecialistCalendarSettings.calendar_id != "",
            )
        )
    )

    conditions = []
    if status is not None:
        conditions.append(Specialist.status == status)
    if not include_system:
        conditions.append(Specialist.is_system.is_(False))
    if oauth_missing:
        conditions.append(~oauth_connected_exists)
    if calendar_missing:
        conditions.append(~calendar_selected_exists)
    if inactive_days_gt is not None:
        inactive_threshold_utc = now_utc - timedelta(days=inactive_days_gt)
        conditions.append(
            ~exists(
                select(1)
                .select_from(MessageLog)
                .where(
                    and_(
                        MessageLog.specialist_id == Specialist.specialist_id,
                        MessageLog.created_at >= inactive_threshold_utc,
                    )
                )
            )
        )

    async with async_session_factory() as session:
        total_stmt = select(func.count()).select_from(Specialist)
        if conditions:
            total_stmt = total_stmt.where(*conditions)

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
                SpecialistProfile.specialist_timezone.label("timezone"),
                Specialist.onboarding_master_completed_at,
                Specialist.onboarding_personal_completed_at,
                oauth_connected_exists.label("oauth_connected"),
                calendar_selected_exists.label("calendar_selected"),
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
        if conditions:
            stmt = stmt.where(*conditions)

        stmt = stmt.order_by(Specialist.created_at.desc()).limit(limit_value).offset(offset)
        rows = (await session.execute(stmt)).all()
        total = int((await session.execute(total_stmt)).scalar_one())

    def _is_active_7d(last_activity_at: datetime | None) -> bool:
        if last_activity_at is None:
            return False
        if last_activity_at.tzinfo is None:
            last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)
        return last_activity_at >= active_since_utc

    items = [
        {
            "specialist_id": str(row.specialist_id),
            "public_name": row.public_name,
            "status": row.status.value if row.status is not None else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tariff_plan": row.tariff_plan.value if row.tariff_plan is not None else None,
            "timezone": row.timezone,
            "onboarding_master_done": bool(row.onboarding_master_completed_at) if row.onboarding_master_completed_at is not None else False,
            "onboarding_personal_done": bool(row.onboarding_personal_completed_at) if row.onboarding_personal_completed_at is not None else False,
            "oauth_connected": bool(row.oauth_connected),
            "calendar_selected": bool(row.calendar_selected),
            "clients_count": int(row.clients_count or 0),
            "last_activity_at": row.last_activity_at.isoformat() if row.last_activity_at else None,
            "active_7d": _is_active_7d(row.last_activity_at),
        }
        for row in rows
    ]

    return {"items": items, "limit": limit_value, "offset": offset, "total": total}


async def build_admin_specialist_detail_payload(
    specialist_id: uuid.UUID,
    *,
    include_system: bool = False,
) -> dict[str, object] | None:
    now_utc = datetime.now(timezone.utc)
    active_since_utc = now_utc - timedelta(days=7)

    oauth_connected_exists = exists(
        select(1)
        .select_from(GoogleOAuth)
        .where(
            and_(
                GoogleOAuth.specialist_id == Specialist.specialist_id,
                GoogleOAuth.refresh_token_encrypted != "",
                GoogleOAuth.status == GoogleOAuthStatus.connected,
            )
        )
    )

    async with async_session_factory() as session:
        stmt = (
            select(
                Specialist.specialist_id,
                Specialist.status,
                Specialist.is_system,
                Specialist.created_at,
                Specialist.onboarding_master_completed_at,
                Specialist.onboarding_personal_completed_at,
                SpecialistProfile.public_name,
                SpecialistProfile.tariff_plan,
                SpecialistProfile.specialist_timezone,
                SpecialistProfile.slot_step_min,
                SpecialistProfile.max_sessions_per_day,
                SpecialistAuthTelegram.tg_username,
                SpecialistAuthTelegram.tg_first_name,
                oauth_connected_exists.label("oauth_connected"),
                SpecialistCalendarSettings.calendar_id,
            )
            .outerjoin(SpecialistProfile, SpecialistProfile.specialist_id == Specialist.specialist_id)
            .outerjoin(SpecialistAuthTelegram, SpecialistAuthTelegram.specialist_id == Specialist.specialist_id)
            .outerjoin(
                SpecialistCalendarSettings,
                SpecialistCalendarSettings.specialist_id == Specialist.specialist_id,
            )
            .where(Specialist.specialist_id == specialist_id)
        )

        if not include_system:
            stmt = stmt.where(Specialist.is_system.is_(False))

        row = (await session.execute(stmt)).one_or_none()
        if row is None:
            return None

        clients_count_stmt = select(func.count(Client.client_id)).where(Client.specialist_id == specialist_id)
        last_activity_stmt = select(func.max(MessageLog.created_at)).where(MessageLog.specialist_id == specialist_id)

        recent_events_stmt = (
            select(MessageLog.created_at, MessageLog.direction, MessageLog.message_type)
            .where(MessageLog.specialist_id == specialist_id)
            .order_by(desc(MessageLog.created_at))
            .limit(20)
        )

        clients_count = int((await session.execute(clients_count_stmt)).scalar_one() or 0)
        last_activity_at = (await session.execute(last_activity_stmt)).scalar_one()
        recent_events_rows = (await session.execute(recent_events_stmt)).all()

    if last_activity_at is not None and last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=timezone.utc)

    active_7d = bool(last_activity_at and last_activity_at >= active_since_utc)

    recent_events = [
        {
            "timestamp": event.created_at.isoformat() if event.created_at else None,
            "event_type": f"{event.direction.value}:{event.message_type}",
        }
        for event in recent_events_rows
        if event.created_at is not None and event.direction is not None and event.message_type
    ]

    return {
        "basic": {
            "specialist_id": str(row.specialist_id),
            "public_name": row.public_name or str(row.specialist_id),
            "status": row.status.value if row.status else None,
            "is_system": bool(row.is_system),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "tariff_plan": row.tariff_plan.value if row.tariff_plan else None,
            "telegram_username": row.tg_username,
            "telegram_first_name": row.tg_first_name,
        },
        "integration": {
            "oauth_connected": bool(row.oauth_connected),
            "calendar_selected": bool(row.calendar_id),
            "selected_calendar_id": row.calendar_id if row.calendar_id else None,
            "timezone": row.specialist_timezone,
            "slot_step": int(row.slot_step_min) if row.slot_step_min is not None else None,
            "max_sessions_per_day": int(row.max_sessions_per_day) if row.max_sessions_per_day is not None else None,
            "onboarding_master_done": bool(row.onboarding_master_completed_at) if row.onboarding_master_completed_at is not None else False,
            "onboarding_personal_done": bool(row.onboarding_personal_completed_at) if row.onboarding_personal_completed_at is not None else False,
        },
        "activity": {
            "clients_count": clients_count,
            "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
            "active_7d": active_7d,
            "recent_events": recent_events,
        },
        "errors": [],
    }


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
    oauth_missing: bool = Query(default=False),
    calendar_missing: bool = Query(default=False),
    inactive_days_gt: int | None = Query(default=None, ge=1),
    _auth: None = Depends(require_admin_key),
):
    return await build_admin_specialists_payload(
        limit=limit,
        offset=offset,
        status=status,
        include_system=include_system,
        oauth_missing=oauth_missing,
        calendar_missing=calendar_missing,
        inactive_days_gt=inactive_days_gt,
    )


@router.get("/specialists/{specialist_id}")
async def admin_specialist_detail(
    specialist_id: str,
    request: Request,
    include_system: bool = Query(default=False),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    specialist_uuid = parse_uuid(specialist_id)

    if config.ADMIN_API_KEY and x_api_key == config.ADMIN_API_KEY:
        payload = await build_admin_specialist_detail_payload(
            specialist_uuid,
            include_system=include_system,
        )
        if payload is None:
            raise HTTPException(status_code=404, detail="Not found")
        return payload

    accept_header = request.headers.get("accept", "")
    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if (
        "text/html" in accept_header
        and bool(config.ADMIN_UI_PASSWORD)
        and admin_ui_session.verify_admin_session_cookie(cookie_value)
    ):
        specialist_id_str = str(specialist_uuid)
        return HTMLResponse(
            content=(
                "<html><body>"
                "<p><a href='/admin#specialists'>← Back to specialists</a></p>"
                "<h1 id='title'>Specialist: ...</h1>"
                "<p id='state'>Loading specialist…</p>"
                "<section id='basic' style='display:none;'><h2>Basic</h2><table border='1' cellpadding='6' style='border-collapse: collapse;'><tbody id='basic-body'></tbody></table></section>"
                "<section id='integration' style='display:none;'><h2>Integration</h2><ul id='integration-list'></ul></section>"
                "<section id='activity' style='display:none;'><h2>Activity</h2><ul id='activity-metrics'></ul><h3>Recent events</h3><ul id='recent-events'></ul></section>"
                "<section id='errors' style='display:none;'><h2>Errors</h2><ul id='errors-list'></ul><p id='no-errors' style='display:none;'>No errors found</p></section>"
                "<script>"
                f"const specialistId='{specialist_id_str}';"
                "const stateEl=document.getElementById('state');"
                "const titleEl=document.getElementById('title');"
                "const basicBodyEl=document.getElementById('basic-body');"
                "const integrationListEl=document.getElementById('integration-list');"
                "const activityMetricsEl=document.getElementById('activity-metrics');"
                "const recentEventsEl=document.getElementById('recent-events');"
                "const errorsListEl=document.getElementById('errors-list');"
                "const noErrorsEl=document.getElementById('no-errors');"
                "const basicSection=document.getElementById('basic');"
                "const integrationSection=document.getElementById('integration');"
                "const activitySection=document.getElementById('activity');"
                "const errorsSection=document.getElementById('errors');"
                "function addBasicRow(label,value){const tr=document.createElement('tr');const tdKey=document.createElement('td');const tdValue=document.createElement('td');tdKey.textContent=label;tdValue.textContent=value===null||value===undefined?'':String(value);tr.appendChild(tdKey);tr.appendChild(tdValue);basicBodyEl.appendChild(tr);}"
                "function addListItem(container,label,value){const li=document.createElement('li');li.textContent=label+': '+(value===null||value===undefined?'':String(value));container.appendChild(li);}"
                "async function loadDetail(){"
                "try{"
                "const res=await fetch('/admin/ui/specialists/'+specialistId,{credentials:'same-origin'});"
                "if(!res.ok){throw new Error('failed');}"
                "const data=await res.json();"
                "const publicName=(data.basic&&data.basic.public_name)?data.basic.public_name:specialistId;"
                "titleEl.textContent='Specialist: '+publicName;"
                "stateEl.style.display='none';"
                "addBasicRow('specialist_id',data.basic.specialist_id);"
                "addBasicRow('public_name',data.basic.public_name);"
                "addBasicRow('status',data.basic.status);"
                "addBasicRow('is_system',data.basic.is_system);"
                "addBasicRow('created_at',data.basic.created_at);"
                "addBasicRow('tariff_plan',data.basic.tariff_plan);"
                "addBasicRow('telegram_username',data.basic.telegram_username);"
                "addBasicRow('telegram_first_name',data.basic.telegram_first_name);"
                "addListItem(integrationListEl,'oauth_connected',data.integration.oauth_connected?'connected':'missing');"
                "addListItem(integrationListEl,'calendar_selected',data.integration.calendar_selected?'selected':'not selected');"
                "addListItem(integrationListEl,'selected_calendar_id',data.integration.selected_calendar_id);"
                "addListItem(integrationListEl,'timezone',data.integration.timezone);"
                "addListItem(integrationListEl,'slot_step',data.integration.slot_step);"
                "addListItem(integrationListEl,'max_sessions_per_day',data.integration.max_sessions_per_day);"
                "addListItem(integrationListEl,'onboarding_master_done',data.integration.onboarding_master_done);"
                "addListItem(integrationListEl,'onboarding_personal_done',data.integration.onboarding_personal_done);"
                "addListItem(activityMetricsEl,'clients_count',data.activity.clients_count);"
                "addListItem(activityMetricsEl,'last_activity_at',data.activity.last_activity_at);"
                "addListItem(activityMetricsEl,'active_7d',data.activity.active_7d);"
                "const events=Array.isArray(data.activity.recent_events)?data.activity.recent_events:[];"
                "if(events.length===0){addListItem(recentEventsEl,'event','No recent events');}else{events.forEach((event)=>{const li=document.createElement('li');li.textContent=(event.timestamp||'')+' — '+(event.event_type||'');recentEventsEl.appendChild(li);});}"
                "const errors=Array.isArray(data.errors)?data.errors:[];"
                "if(errors.length===0){noErrorsEl.style.display='block';}else{errors.forEach((err)=>{const li=document.createElement('li');li.textContent=(err.timestamp||'')+' ['+(err.type||'')+'] '+(err.message||'');errorsListEl.appendChild(li);});}"
                "basicSection.style.display='block';integrationSection.style.display='block';activitySection.style.display='block';errorsSection.style.display='block';"
                "}catch(_e){stateEl.textContent='Failed to load';}"
                "}"
                "loadDetail();"
                "</script>"
                "</body></html>"
            ),
            status_code=200,
        )

    if "text/html" in accept_header:
        raise HTTPException(status_code=404, detail="Not found")

    raise HTTPException(status_code=403, detail="Forbidden")


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
