import json
import asyncio
import logging
import mimetypes
import os
import re
import fnmatch
import smtplib
import secrets
import time
import uuid
from email.message import EmailMessage
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs
import requests
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import Text, cast, delete, func, select, text, update
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    Appointment,
    AppointmentReminder,
    BookingState,
    BillingPeriod,
    Client,
    LogDirection,
    Specialist,
    SpecialistPublicMedia,
    SpecialistPublicProfile,
    SpecialistStatus,
    TariffPlan,
    async_session_factory, 
    GoogleOAuth, 
    GoogleOAuthStatus, 
    OAuthState,
    OAuthStateType,
    SpecialistAuthTelegram,
    SpecialistProfile,
    CalendarSyncState,
    ServiceHeartbeat,
    AdminAuditLog,
    AdminBulkCleanupJob,
    NotificationLog,
    OutboxEvent,
    TelegramBot,
    TelegramBotStatus,
)
from services.google_oauth import create_oauth_state, exchange_code_for_token_async, get_auth_url
from services.referrals import process_referral_activation
from services.tariff_access import AnalyticsAccessError, ensure_analytics_access, ANALYTICS_PRO_REQUIRED_ERROR
from services.google_calendar import (
    GoogleCalendarInsufficientPermissionsError,
    list_calendars,
    required_scopes,
    scopes_as_string,
)
from services.google_calendar_reverse_sync import run_calendar_reverse_sync
from services.crypto import encrypt_token
from logging_middleware import log_outbound_message
from services import heartbeat
from services.telegram.bot_factory import close_personal_bot_cache
from services.telegram.personal_dispatcher import process_update
from services.build_info import get_build_info
from services.media_storage import remove_file_if_exists
from services.request_context import get_request_id, reset_request_id, set_request_id
from services.alerting import close_alerting, notify_exception
from services import admin_ui_session, web_connect, web_session
import config
from admin_api import (
    build_admin_specialist_detail_payload,
    build_admin_specialists_payload,
    build_heartbeat_query,
    build_message_log_query,
    compute_admin_overview,
    clamp_limit,
    router as admin_router,
)
from services.log_exporter import parse_iso_datetime, serialize_message_log, serialize_service_heartbeat
from services.admin_audit import build_admin_audit_log_query, sanitize_admin_audit_payload_for_ui, write_admin_audit_log
from services.billing.subscriptions import (
    BillingError,
    create_yookassa_payment_for_token,
    get_purchase_for_raw_token,
    process_yookassa_webhook,
)
from backend.api.public_specialist import router as public_specialist_router
from backend.api.specialist_profile_private import router as specialist_profile_private_router
from frontend.router import resolve_frontend_route

logger = logging.getLogger(__name__)

_UNKNOWN_CHANNEL_LOG_WINDOW_SECONDS = 600
_unknown_channel_log_state: dict[str, tuple[float, int]] = {}


def _should_log_unknown_channel(channel_id: str) -> tuple[bool, int]:
    now_monotonic = time.monotonic()
    next_allowed_at, suppressed_count = _unknown_channel_log_state.get(channel_id, (0.0, 0))
    if now_monotonic >= next_allowed_at:
        _unknown_channel_log_state[channel_id] = (now_monotonic + _UNKNOWN_CHANNEL_LOG_WINDOW_SECONDS, 0)
        return True, suppressed_count

    _unknown_channel_log_state[channel_id] = (next_allowed_at, suppressed_count + 1)
    return False, suppressed_count + 1

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = WEB_DIR / "assets"
INDEX_FILE = WEB_DIR / "index.html"

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = request_id
        return response


def _csrf_protected_admin_ui_post(request: Request) -> bool:
    return request.method.upper() == "POST" and request.url.path.startswith("/admin/ui/")


def _request_id_from_request(request: Request) -> str:
    return getattr(request.state, "request_id", get_request_id())


async def _run_storage_cleanup_job(payload: dict) -> None:
    logger.info("event=admin_test_specialist_storage_cleanup_scheduled payload=%s", payload)


def _schedule_storage_cleanup(payload: dict) -> None:
    asyncio.create_task(_run_storage_cleanup_job(payload))


def _reset_confirmation_phrase(specialist_id: uuid.UUID) -> str:
    return f"RESET TEST DATA {specialist_id}"


def _issue_reset_token(specialist_id: uuid.UUID) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=RESET_TEST_DATA_CONFIRMATION_TTL_SECONDS)
    with _reset_test_data_tokens_lock:
        _reset_test_data_tokens[token] = {
            "specialist_id": specialist_id,
            "expires_at": expires_at,
            "confirmed": False,
            "used": False,
        }
    return token, expires_at


def _get_reset_token_state(token: str) -> dict[str, object] | None:
    with _reset_test_data_tokens_lock:
        state = _reset_test_data_tokens.get(token)
        if state is None:
            return None

        expires_at = state.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
            _reset_test_data_tokens.pop(token, None)
            return None
        return dict(state)


def _set_reset_token_confirmed(token: str) -> bool:
    with _reset_test_data_tokens_lock:
        state = _reset_test_data_tokens.get(token)
        if state is None:
            return False
        expires_at = state.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
            _reset_test_data_tokens.pop(token, None)
            return False
        if state.get("used"):
            return False
        state["confirmed"] = True
        return True


def _consume_reset_token(token: str, specialist_id: uuid.UUID) -> bool:
    with _reset_test_data_tokens_lock:
        state = _reset_test_data_tokens.get(token)
        if state is None:
            return False
        expires_at = state.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at < datetime.now(timezone.utc):
            _reset_test_data_tokens.pop(token, None)
            return False
        if state.get("used") or not state.get("confirmed"):
            return False
        if state.get("specialist_id") != specialist_id:
            return False
        state["used"] = True
        return True


def _cleanup_reset_tokens_for_specialist(specialist_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    with _reset_test_data_tokens_lock:
        to_delete = []
        for token, state in _reset_test_data_tokens.items():
            expires_at = state.get("expires_at")
            if isinstance(expires_at, datetime) and expires_at < now:
                to_delete.append(token)
                continue
            if state.get("specialist_id") == specialist_id:
                to_delete.append(token)
        for token in to_delete:
            _reset_test_data_tokens.pop(token, None)


async def _count_reset_test_data(session, specialist_id: uuid.UUID) -> dict[str, int]:
    clients = int((await session.execute(select(func.count()).select_from(Client).where(Client.specialist_id == specialist_id))).scalar_one())
    appointments = int((await session.execute(select(func.count()).select_from(Appointment).where(Appointment.specialist_id == specialist_id))).scalar_one())

    notification_like = f"%{specialist_id}%"
    notifications = int(
        (
            await session.execute(
                select(func.count(NotificationLog.id))
                .select_from(NotificationLog)
                .join(OutboxEvent, OutboxEvent.id == NotificationLog.outbox_event_id)
                .where(cast(OutboxEvent.payload_json, Text).like(notification_like))
            )
        ).scalar_one()
    )

    media = int(
        (
            await session.execute(
                select(func.count())
                .select_from(SpecialistPublicMedia)
                .join(SpecialistPublicProfile, SpecialistPublicProfile.id == SpecialistPublicMedia.profile_id)
                .where(SpecialistPublicProfile.specialist_id == specialist_id)
            )
        ).scalar_one()
    )
    return {
        "clients": clients,
        "appointments": appointments,
        "notifications": notifications,
        "media": media,
    }


async def _delete_reset_test_data_runtime_rows(session, specialist_id: uuid.UUID) -> dict[str, int]:
    deleted_counts: dict[str, int] = {
        "appointments": 0,
        "appointment_reminders": 0,
        "clients": 0,
        "notifications": 0,
        "outbox_events": 0,
        "media": 0,
    }

    appointment_ids = (
        await session.execute(select(Appointment.appointment_id).where(Appointment.specialist_id == specialist_id))
    ).scalars().all()

    if appointment_ids:
        deleted_reminders = await session.execute(
            delete(AppointmentReminder).where(AppointmentReminder.appointment_id.in_(appointment_ids))
        )
        deleted_counts["appointment_reminders"] = int(deleted_reminders.rowcount or 0)

    deleted_appointments = await session.execute(delete(Appointment).where(Appointment.specialist_id == specialist_id))
    deleted_counts["appointments"] = int(deleted_appointments.rowcount or 0)

    deleted_clients = await session.execute(delete(Client).where(Client.specialist_id == specialist_id))
    deleted_counts["clients"] = int(deleted_clients.rowcount or 0)

    payload_like = f"%{specialist_id}%"
    outbox_ids = (
        await session.execute(select(OutboxEvent.id).where(cast(OutboxEvent.payload_json, Text).like(payload_like)))
    ).scalars().all()
    if outbox_ids:
        deleted_notifications = await session.execute(
            delete(NotificationLog).where(NotificationLog.outbox_event_id.in_(outbox_ids))
        )
        deleted_counts["notifications"] = int(deleted_notifications.rowcount or 0)

        deleted_outbox = await session.execute(delete(OutboxEvent).where(OutboxEvent.id.in_(outbox_ids)))
        deleted_counts["outbox_events"] = int(deleted_outbox.rowcount or 0)

    media_profile_subquery = select(SpecialistPublicProfile.id).where(
        SpecialistPublicProfile.specialist_id == specialist_id
    )
    deleted_media = await session.execute(
        delete(SpecialistPublicMedia).where(SpecialistPublicMedia.profile_id.in_(media_profile_subquery))
    )
    deleted_counts["media"] = int(deleted_media.rowcount or 0)
    return deleted_counts


def build_calendar_switch_keyboard(*, has_selected_calendar: bool) -> InlineKeyboardMarkup:
    button_text = "📅 Сменить календарь" if has_selected_calendar else "📅 Выбрать календарь"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, callback_data="calendar:switch_stub")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="calendar:cancel_select")],
        ]
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # Закрываем personal bot cache первым, чтобы завершить дочерние HTTP-сессии
    # до закрытия master bot и сделать shutdown более предсказуемым.
    try:
        await close_personal_bot_cache()
        logger.info("Personal bot cache closed on shutdown")
    except Exception:
        logger.warning("Failed to close personal bot cache on shutdown", exc_info=True)

    if bot is not None:
        try:
            await bot.session.close()
            logger.info("Master bot session closed on shutdown")
        except Exception:
            logger.warning("Failed to close master bot session on shutdown", exc_info=True)

    try:
        await close_alerting()
        logger.info("Alerting bot session closed on shutdown")
    except Exception:
        logger.warning("Failed to close alerting bot session on shutdown", exc_info=True)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zumbot.ru",
        "https://www.zumbot.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(public_specialist_router)
app.include_router(specialist_profile_private_router)

if ASSETS_DIR.exists() and INDEX_FILE.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


    SITE_PAGES = {
        "/": "index.html",
        "/features": "features.html",
        "/pricing": "pricing.html",
        "/specialists": "specialists.html",
        "/contacts": "contacts.html",
        "/privacy": "privacy.html",
        "/terms": "terms.html",
        "/revoke-access": "revoke-access.html",
        "/legal": "legal.html",
        "/privacy-ru": "privacy-ru.html",
        "/terms-ru": "terms-ru.html",
        "/revoke-access-ru": "revoke-access-ru.html",
        "/success": "success.html",
        "/profile/edit": "profile-edit.html",
    }

    def _site_file(page: str) -> Path:
        return WEB_DIR / SITE_PAGES[page]

    SITE_BRAND_TEXT = "Zumbot"

    SITE_NAV_LINKS = (
        ("Возможности", "/features"),
        ("Тарифы", "/pricing"),
        ("Для специалистов", "/specialists"),
        ("Контакты", "/contacts"),
    )

    def _site_header_html(page: str) -> str:
        nav_links = []
        for title, href in SITE_NAV_LINKS:
            active_class = ' class="active"' if page == href else ""
            nav_links.append(f'<a href="{href}"{active_class}>{title}</a>')

        nav_html = "".join(nav_links)
        return (
            '<header class="site-header">'
            '<div class="container header-inner">'
            '<a class="logo" href="/">'
            '<img src="/assets/zumbot_logo.png" srcset="/assets/zumbot_logo.png 1x, '
            '/assets/zumbot_logo@2x.png 2x" alt="Zumbot logo" />'
            f'<span class="logo-text">{SITE_BRAND_TEXT}</span>'
            '</a>'
            f'<nav class="main-nav">{nav_html}</nav>'
            '<a href="https://t.me/zumhelper_bot?start=start" class="btn-primary" target="_blank" rel="noopener noreferrer">Подключить</a>'
            '</div>'
            '</header>'
        )

    def _site_footer_html(page: str) -> str:
        ru_pages = {
            "/",
            "/features",
            "/pricing",
            "/specialists",
            "/contacts",
            "/privacy-ru",
            "/terms-ru",
            "/legal",
            "/revoke-access-ru",
            "/success",
        }
        is_ru_page = page in ru_pages

        if is_ru_page:
            nav_links = (
                ("Политика конфиденциальности", "/privacy-ru"),
                ("Пользовательское соглашение", "/terms-ru"),
                ("Реквизиты и правовая информация", "/legal"),
            )
        else:
            nav_links = (
                ("Privacy Policy", "/privacy"),
                ("Terms of Service", "/terms"),
                ("Legal details", "/legal"),
            )

        nav_html = "".join(f'<a href="{href}">{title}</a>' for title, href in nav_links)

        return (
            '<footer class="site-footer">'
            '<div class="container footer-inner">'
            '<a class="logo logo-footer" href="/">'
            '<img src="/assets/zumbot_logo.png" srcset="/assets/zumbot_logo.png 1x, '
            '/assets/zumbot_logo@2x.png 2x" alt="Zumbot logo" />'
            f'<span class="logo-text">{SITE_BRAND_TEXT}</span>'
            '</a>'
            f'<nav>{nav_html}</nav>'
            '<p class="footer-copy">© 2026</p>'
            '<div id="legal-info-footer">'
            'Самозанятый: Босов Александр Михайлович<br />'
            'ИНН: 772644000871<br />'
            'НПД (налог на проф. доход)<br />'
            'Email: info@zumbot.ru<br />'
            'Тел.: +7 (966) 176-36-29'
            '</div>'
            '</div>'
            '</footer>'
        )

    def _render_site_page(page: str, *, include_marketing_chrome: bool = True) -> HTMLResponse:
        html = _site_file(page).read_text(encoding="utf-8")
        if include_marketing_chrome:
            html = html.replace("{{SITE_HEADER}}", _site_header_html(page))
            html = html.replace("{{SITE_FOOTER}}", _site_footer_html(page))
        else:
            html = html.replace("{{SITE_HEADER}}", "")
            html = html.replace("{{SITE_FOOTER}}", "")
        return HTMLResponse(content=html)


    @app.get("/")
    async def site_index() -> HTMLResponse:
        return _render_site_page("/")

    @app.head("/")
    async def site_index_head() -> Response:
        return Response(status_code=200)

    @app.get("/features")
    async def site_features() -> HTMLResponse:
        return _render_site_page("/features")

    @app.get("/pricing")
    async def site_pricing() -> HTMLResponse:
        return _render_site_page("/pricing")

    @app.get("/specialists")
    async def site_specialists() -> HTMLResponse:
        return _render_site_page("/specialists")

    @app.get("/contacts")
    async def site_contacts() -> HTMLResponse:
        return _render_site_page("/contacts")

    @app.get("/privacy")
    async def site_privacy() -> HTMLResponse:
        return _render_site_page("/privacy")

    @app.head("/privacy")
    async def site_privacy_head() -> Response:
        return Response(status_code=200)

    @app.get("/terms")
    async def site_terms() -> HTMLResponse:
        return _render_site_page("/terms")

    @app.head("/terms")
    async def site_terms_head() -> Response:
        return Response(status_code=200)

    @app.get("/revoke-access")
    async def site_revoke_access() -> HTMLResponse:
        return _render_site_page("/revoke-access")

    @app.head("/revoke-access")
    async def site_revoke_access_head() -> Response:
        return Response(status_code=200)

    @app.get("/legal")
    async def site_legal() -> HTMLResponse:
        return _render_site_page("/legal")

    @app.head("/legal")
    async def site_legal_head() -> Response:
        return Response(status_code=200)

    @app.get("/privacy-ru")
    async def site_privacy_ru() -> HTMLResponse:
        return _render_site_page("/privacy-ru")

    @app.head("/privacy-ru")
    async def site_privacy_ru_head() -> Response:
        return Response(status_code=200)

    @app.get("/terms-ru")
    async def site_terms_ru() -> HTMLResponse:
        return _render_site_page("/terms-ru")

    @app.head("/terms-ru")
    async def site_terms_ru_head() -> Response:
        return Response(status_code=200)

    @app.get("/revoke-access-ru")
    async def site_revoke_access_ru() -> HTMLResponse:
        return _render_site_page("/revoke-access-ru")

    @app.head("/revoke-access-ru")
    async def site_revoke_access_ru_head() -> Response:
        return Response(status_code=200)

    @app.get("/success")
    async def site_success() -> HTMLResponse:
        return _render_site_page("/success")

    @app.get("/profile/edit")
    async def site_profile_edit() -> HTMLResponse:
        return _render_site_page("/profile/edit", include_marketing_chrome=False)

else:
    logger.warning(
        "Static site disabled: expected index=%s assets_dir=%s",
        INDEX_FILE,
        ASSETS_DIR,
    )

    @app.get("/success", response_class=HTMLResponse)
    async def site_success_fallback() -> HTMLResponse:
        return HTMLResponse(
            "<h1>Готово</h1>"
            "<p>Google Календарь подключён. Вернитесь в Telegram, чтобы продолжить настройку.</p>"
            '<p><a href="https://t.me/zumhelper_bot" target="_blank" rel="noopener noreferrer">Открыть Telegram</a></p>'
        )


@app.get("/media/{file_key:path}")
async def get_public_media(file_key: str):
    normalized = str(file_key or "").lstrip("/")
    if not normalized or ".." in normalized.split("/"):
        raise HTTPException(status_code=404, detail="not_found")

    async with async_session_factory() as session:
        media_row = (
            await session.execute(
                select(SpecialistPublicMedia.file_key)
                .where(
                    SpecialistPublicMedia.media_type == "photo",
                    SpecialistPublicMedia.file_key == normalized,
                )
                .limit(1)
            )
        ).scalar_one_or_none()

    if media_row is None:
        raise HTTPException(status_code=404, detail="not_found")

    uploads_root = Path(config.PROFILE_UPLOADS_DIR).resolve()
    path = (uploads_root / normalized).resolve()
    if uploads_root not in path.parents:
        raise HTTPException(status_code=404, detail="not_found")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not_found")
    guessed_type, _encoding = mimetypes.guess_type(path.name)
    media_type = guessed_type if guessed_type in {"image/jpeg", "image/png", "image/webp"} else None
    return FileResponse(path=path, media_type=media_type)

READYZ_DB_TIMEOUT_SEC = 2.0
READYZ_LOOP_TIMEOUT_SEC = 12.0
HEARTBEAT_WRITE_INTERVAL_SEC = 60.0
SERVICE_NAME = config.SERVICE_NAME
LAST_HEARTBEAT_WRITE_TS = 0.0
HEARTBEAT_WRITE_LOCK = asyncio.Lock()

MAX_WEBHOOK_BODY_BYTES = config.MAX_WEBHOOK_BODY_BYTES
GOOGLE_CALENDAR_REVERSE_SYNC_THROTTLE_SECONDS = 15

# Инициализируем бота для отправки уведомлений (используем тот же токен)
bot = None
if config.MASTER_BOT_TOKEN:
    try:
        bot = Bot(
            token=config.MASTER_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
    except Exception:
        logger.warning("MASTER_BOT_TOKEN is invalid, outbound notifications disabled", exc_info=True)



_PLAN_TITLES = {
    "free": "Free",
    "start": "Start",
    "pro": "Pro",
    "team": "Team",
}

_PERIOD_TITLES = {
    BillingPeriod.monthly.value: "Месяц",
    BillingPeriod.yearly.value: "Год",
}


@app.get("/pay", response_class=HTMLResponse)
async def pay_page(token: str = Query(..., min_length=16)) -> HTMLResponse:
    purchase = await get_purchase_for_raw_token(token)
    if purchase is None:
        return HTMLResponse("<h1>Ссылка недействительна</h1><p>Попробуйте сформировать новую ссылку в Telegram-боте.</p>", status_code=404)

    now = datetime.now(timezone.utc)
    if purchase.expires_at <= now:
        return HTMLResponse("<h1>Срок действия ссылки истёк</h1><p>Сформируйте новую ссылку на оплату в Telegram-боте.</p>", status_code=410)
    if purchase.used_at is not None:
        return HTMLResponse("<h1>Ссылка уже использована</h1><p>Сформируйте новую ссылку на оплату в Telegram-боте.</p>", status_code=410)

    plan_title = _PLAN_TITLES.get(purchase.plan.value, purchase.plan.value)
    period_title = _PERIOD_TITLES.get(purchase.period.value, purchase.period.value)
    amount = purchase.amount_rub_int
    html = (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Оплата подписки — Zumbot</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;background:#f7f8fa;margin:0;padding:24px 16px;color:#151515;}"
        ".checkout-wrap{max-width:520px;margin:0 auto;}"
        ".breadcrumb{margin:0 0 12px;font-size:13px;color:#666;}"
        "h1{margin:0 0 12px;font-size:30px;line-height:1.2;}"
        ".service-description{margin:0 0 20px;color:#3f3f3f;line-height:1.5;}"
        ".service-description ul{margin:8px 0 0 18px;padding:0;}"
        ".service-description li{margin:4px 0;}"
        ".checkout-card{max-width:520px;margin:0 auto;border-radius:12px;box-shadow:0 8px 24px rgba(17,17,17,.08);padding:28px;background:#fff;}"
        ".checkout-card p{margin:0 0 12px;line-height:1.4;}"
        ".checkout-card p:last-child{margin-bottom:0;} .subsection{margin-top:20px;padding-top:16px;border-top:1px solid #ededed;}"
        ".subsection h2{margin:0 0 10px;font-size:18px;} .subsection p{margin:0 0 10px;} .subsection ul{margin:8px 0 0 18px;padding:0;}"
        ".support-email{font-weight:700;color:#3a3a3a;}"
        ".muted{color:#6e6e6e;}"
        ".provider-note{margin-top:16px;text-align:center;font-size:14px;}"
        ".btn{display:block;margin-top:18px;background:#111;color:#fff;padding:12px 16px;border-radius:10px;text-decoration:none;border:none;cursor:pointer;text-align:center;font-weight:700;}"
        ".btn-subtitle{margin-top:10px;text-align:center;font-size:13px;}"
        ".legal-line{margin-top:12px;text-align:center;font-size:13px;}"
        ".legal-line a{color:#3d3d3d;}"
        "@media (max-width:480px){body{padding:20px 12px;}h1{font-size:24px;}.checkout-card{padding:20px;}.btn{padding:12px;width:100%;box-sizing:border-box;}}"
        "</style></head><body>"
        "<div class='checkout-wrap'>"
        "<p class='breadcrumb'>Zumbot → Оплата подписки</p>"
        "<h1>Подписка на сервис Zumbot</h1>"
        "<div class='service-description'>"
        "<p>Zumbot — сервис автоматизации записи клиентов для специалистов.</p>"
        "<p>Сервис позволяет:</p>"
        "<ul><li>принимать онлайн-записи</li><li>автоматически синхронизировать расписание с Google Calendar</li><li>отправлять напоминания клиентам в Telegram</li><li>вести базовую статистику записей.</li></ul>"
        "</div>"
        "<div class='checkout-card'>"
        f"<p><strong>Тариф подписки:</strong> {plan_title}</p>"
        f"<p><strong>Период подписки:</strong> {period_title}</p>"
        f"<p><strong>Стоимость:</strong> {amount} ₽</p>"
        "<p class='muted'>Статус: ожидает оплаты</p>"
        f"<a class='btn' href='/pay/confirm?token={token}'>Перейти к оплате</a>"
        "<p class='muted btn-subtitle'>Вы будете перенаправлены на защищенную страницу оплаты.</p>"
        "<p class='muted btn-subtitle'>Платеж обрабатывается через защищенную платежную систему ЮKassa.</p>"
        "<div class='subsection muted'>"
        "<h2>Поддержка</h2>"
        "<p>Если у вас возникли вопросы по оплате или работе сервиса, напишите нам:</p>"
        "<p class='support-email'>info@zumbot.ru</p>"
        "</div>"
        "<p class='legal-line muted'>Оплачивая подписку, вы соглашаетесь с условиями сервиса. "
        "<a href='/terms' target='_blank' rel='noopener noreferrer'>/terms</a> "
        "<a href='/privacy' target='_blank' rel='noopener noreferrer'>/privacy</a></p>"
        "<div class='subsection'>"
        "<h2>Условия подписки</h2>"
        "<p>Вы оформляете подписку на SaaS-сервис Zumbot — систему автоматизации записи клиентов.</p>"
        "<p>Подписка включает:</p>"
        "<ul><li>использование Telegram-бота для записи клиентов</li><li>синхронизацию расписания с Google Calendar</li><li>напоминания клиентам</li><li>инструменты аналитики и управления записью.</li></ul>"
        "<p>Период подписки: 1 месяц.</p>"
        "<p>Оплата производится за выбранный период. Продление подписки осуществляется вручную через интерфейс сервиса.</p>"
        "</div>"
        "</div>"
        "<p class='muted provider-note'>Оплата осуществляется через платежную систему ЮKassa.</p>"
        "</div></body></html>"
    )
    return HTMLResponse(html)


@app.get('/pay/confirm')
async def pay_confirm(token: str = Query(..., min_length=16)):
    try:
        confirmation_url = await create_yookassa_payment_for_token(token)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RedirectResponse(url=confirmation_url, status_code=303)


@app.post('/api/billing/yookassa/create')
async def api_billing_yookassa_create(payload: dict):
    token = str(payload.get('token') or '').strip()
    if not token:
        raise HTTPException(status_code=422, detail='token is required')
    try:
        confirmation_url = await create_yookassa_payment_for_token(token)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {'ok': True, 'confirmation_url': confirmation_url}


@app.post('/api/billing/yookassa/webhook')
async def api_billing_yookassa_webhook(request: Request):
    if config.YOOKASSA_WEBHOOK_SECRET:
        got = request.headers.get('x-zumbot-webhook-secret', '')
        if got != config.YOOKASSA_WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail='unauthorized')

    payload = await request.json()
    try:
        status = await process_yookassa_webhook(payload)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {'ok': True, 'status': status}

logger.info("readyz endpoint enabled=%s", config.ENABLE_READYZ)
if config.ADMIN_API_KEY:
    app.include_router(admin_router)
    logger.info("admin API enabled at /admin/*")
else:
    logger.info("admin API disabled (ADMIN_API_KEY not set)")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "backend", **get_build_info()}


def require_admin_key_hidden_404(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not config.ADMIN_API_KEY or x_api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=404, detail="Not found")


ADMIN_UI_COOKIE_NAME = "admin_session"
ADMIN_UI_CSRF_COOKIE_NAME = "admin_csrf"
ADMIN_UI_CSRF_HEADER_NAME = "X-CSRF-Token"
ADMIN_UI_SESSION_TTL_HOURS = config.ADMIN_SESSION_TTL_HOURS
BULK_DELETE_TEST_ACCOUNTS_CONFIRMATION_PHRASE = "DELETE ALL TEST ACCOUNTS"
RESET_TEST_DATA_CONFIRMATION_TTL_SECONDS = 300

_reset_test_data_tokens: dict[str, dict[str, object]] = {}
_reset_test_data_tokens_lock = Lock()


class AdminBulkDeleteAllRequest(BaseModel):
    confirmation_phrase: str


class AdminResetTestDataRequest(BaseModel):
    step: str = Field(pattern="^(preflight|confirm|execute)$")
    confirmation_token: str | None = None
    confirmation_phrase: str | None = None


class AdminDiagnosticRunRequest(BaseModel):
    check_type: str = Field(pattern="^(orphan_specialist_media_scan|server_clutter_scan)$")


def _admin_ui_enabled() -> bool:
    return bool(config.ADMIN_UI_PASSWORD)


def _admin_ui_cookie_secure() -> bool:
    return True


def _raise_not_found() -> None:
    raise HTTPException(status_code=404, detail="Not found")


def _count_severity(findings: list[dict[str, object]], severity: str) -> int:
    return sum(1 for finding in findings if finding.get("severity") == severity)


async def _run_orphan_specialist_media_scan() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    db_keys: set[str] = set()
    uploads_root = Path(config.PROFILE_UPLOADS_DIR)

    async with async_session_factory() as session:
        rows = (await session.execute(select(SpecialistPublicMedia.file_key))).scalars().all()

    for raw_key in rows:
        key = str(raw_key or "").lstrip("/")
        if not key:
            continue
        db_keys.add(key)
        if not (uploads_root / key).is_file():
            findings.append(
                {
                    "severity": "high",
                    "code": "MISSING_MEDIA_FILE",
                    "entity_ref": f"db:file_key:{key}",
                    "message": "DB reference points to missing storage file",
                    "recommended_action": "Restore file or remove stale reference in dedicated remediation flow",
                }
            )

    storage_keys: set[str] = set()
    specialist_root = uploads_root / "specialist"
    if specialist_root.exists():
        for path in specialist_root.rglob("*"):
            if not path.is_file():
                continue
            storage_key = path.relative_to(uploads_root).as_posix()
            storage_keys.add(storage_key)

    for storage_key in sorted(storage_keys - db_keys):
        findings.append(
            {
                "severity": "medium",
                "code": "ORPHAN_MEDIA_OBJECT",
                "entity_ref": f"storage:{storage_key}",
                "message": "Storage file has no DB reference",
                "recommended_action": "Review and remove in a separate cleanup workflow",
            }
        )

    scanned = len(db_keys) + len(storage_keys)
    return {
        "summary": {
            "scanned": scanned,
            "findings_total": len(findings),
            "high": _count_severity(findings, "high"),
            "medium": _count_severity(findings, "medium"),
            "low": _count_severity(findings, "low"),
        },
        "findings": findings,
    }


def _is_path_allowed(path: Path, allowlisted_roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in allowlisted_roots:
        root_resolved = root.resolve()
        if resolved == root_resolved or root_resolved in resolved.parents:
            return True
    return False


def _build_server_clutter_allowlist() -> list[Path]:
    roots = [Path(config.PROFILE_UPLOADS_DIR)]
    if config.LOG_DIR:
        roots.append(Path(config.LOG_DIR))
    uniq: dict[str, Path] = {}
    for root in roots:
        uniq[str(root.resolve())] = root
    return list(uniq.values())


def _safe_entity_ref(path: Path, *, root: Path) -> str:
    try:
        rel = path.relative_to(root)
        return f"{root.name}/{rel.as_posix()}"
    except ValueError:
        return path.name


def _run_server_clutter_scan() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    allowlisted_roots = _build_server_clutter_allowlist()
    patterns: list[tuple[str, str, str]] = [
        ("*.bak", "high", "STRAY_BACKUP_FILE"),
        ("*.old", "high", "STRAY_BACKUP_FILE"),
        ("*.tmp", "medium", "TEMP_ARTIFACT"),
        ("*.swp", "medium", "EDITOR_SWAP_ARTIFACT"),
        ("*~", "low", "EDITOR_BACKUP_ARTIFACT"),
        ("*.sql.dump", "high", "DB_DUMP_ARTIFACT"),
        ("*.sqlite3", "medium", "SQLITE_DEV_ARTIFACT"),
    ]

    scanned = 0
    max_findings = 200
    for root in allowlisted_roots:
        if not root.exists() or not root.is_dir():
            continue
        for current_root, dirnames, filenames in os.walk(root, followlinks=False):
            current_root_path = Path(current_root)
            dirnames[:] = [d for d in dirnames if not (current_root_path / d).is_symlink()]
            for filename in filenames:
                path = current_root_path / filename
                if path.is_symlink() or not path.is_file() or not _is_path_allowed(path, allowlisted_roots):
                    continue
                scanned += 1
                name = path.name
                for pattern, severity, code in patterns:
                    if fnmatch.fnmatch(name, pattern):
                        findings.append(
                            {
                                "severity": severity,
                                "code": code,
                                "entity_ref": _safe_entity_ref(path, root=root),
                                "message": f"Matched server clutter pattern {pattern}",
                                "recommended_action": "Review and remove via dedicated remediation process",
                            }
                        )
                        break

                if len(findings) >= max_findings:
                    findings.append(
                        {
                            "severity": "low",
                            "code": "RESULT_TRUNCATED",
                            "entity_ref": root.name,
                            "message": "Findings truncated at safety limit",
                            "recommended_action": "Narrow scan scope in next run",
                        }
                    )
                    break

            if len(findings) >= max_findings:
                break

        if len(findings) >= max_findings:
            break

    return {
        "summary": {
            "scanned": scanned,
            "findings_total": len(findings),
            "high": _count_severity(findings, "high"),
            "medium": _count_severity(findings, "medium"),
            "low": _count_severity(findings, "low"),
        },
        "findings": findings,
    }


async def _execute_diagnostic(check_type: str) -> dict[str, object]:
    if check_type == "orphan_specialist_media_scan":
        return await _run_orphan_specialist_media_scan()
    if check_type == "server_clutter_scan":
        return _run_server_clutter_scan()
    raise ValueError("unsupported_check_type")


@app.middleware("http")
async def admin_ui_csrf_middleware(request: Request, call_next):
    if not _csrf_protected_admin_ui_post(request):
        return await call_next(request)

    if not _admin_ui_enabled():
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    session_cookie = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(session_cookie):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    csrf_cookie = request.cookies.get(ADMIN_UI_CSRF_COOKIE_NAME, "")
    csrf_header = request.headers.get(ADMIN_UI_CSRF_HEADER_NAME, "")
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})

    return await call_next(request)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page() -> HTMLResponse:
    if not _admin_ui_enabled():
        _raise_not_found()

    return HTMLResponse(
        content=(
            "<html><body>"
            "<h1>Zumbot Admin Login</h1>"
            '<form method="post" action="/admin/login">'
            '<label for="password">Password</label>'
            '<input id="password" type="password" name="password" autocomplete="current-password" required />'
            '<button type="submit">Login</button>'
            "</form>"
            "</body></html>"
        ),
        status_code=200,
    )


@app.post("/admin/login")
async def admin_login(request: Request) -> Response:
    form_data = parse_qs((await request.body()).decode("utf-8"))
    password = form_data.get("password", [""])[0]
    request_id = _request_id_from_request(request)
    request_ip = request.client.host if request.client else "unknown"
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    if not _admin_ui_enabled() or password != config.ADMIN_UI_PASSWORD:
        logger.info(
            "event=admin_login_failed timestamp=%s ip=%s request_id=%s reason=invalid_password",
            timestamp_utc,
            request_ip,
            request_id,
        )
        _raise_not_found()

    logger.info(
        "event=admin_login_success timestamp=%s ip=%s request_id=%s",
        timestamp_utc,
        request_ip,
        request_id,
    )

    session_cookie = admin_ui_session.sign_admin_session_cookie(ttl_hours=ADMIN_UI_SESSION_TTL_HOURS)
    csrf_token = secrets.token_urlsafe(32)
    session_expires_at = datetime.now(timezone.utc) + timedelta(hours=ADMIN_UI_SESSION_TTL_HOURS)
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key=ADMIN_UI_COOKIE_NAME,
        value=session_cookie,
        max_age=ADMIN_UI_SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=_admin_ui_cookie_secure(),
        samesite="lax",
        path="/admin",
        expires=session_expires_at,
    )
    response.set_cookie(
        key=ADMIN_UI_CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=ADMIN_UI_SESSION_TTL_HOURS * 3600,
        httponly=False,
        secure=_admin_ui_cookie_secure(),
        samesite="lax",
        path="/admin",
    )
    return response


@app.post("/admin/logout")
async def admin_logout() -> Response:
    if not _admin_ui_enabled():
        _raise_not_found()

    admin_ui_session.invalidate_admin_sessions()

    response = JSONResponse(content={"ok": True})
    response.delete_cookie(
        key=ADMIN_UI_COOKIE_NAME,
        path="/admin",
        httponly=True,
        secure=_admin_ui_cookie_secure(),
        samesite="strict",
    )
    response.delete_cookie(
        key=ADMIN_UI_CSRF_COOKIE_NAME,
        path="/admin",
        httponly=False,
        secure=_admin_ui_cookie_secure(),
        samesite="strict",
    )
    return response


@app.get("/admin/ui/specialists")
async def admin_ui_specialists(
    request: Request,
    limit: int | None = Query(default=100),
    offset: int = Query(default=0, ge=0),
    status: SpecialistStatus | None = Query(default=None),
    include_system: bool = Query(default=False),
    oauth_missing: bool = Query(default=False),
    calendar_missing: bool = Query(default=False),
    inactive_days_gt: int | None = Query(default=None, ge=1),
    test_only: bool = Query(default=False),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    return await build_admin_specialists_payload(
        limit=limit,
        offset=offset,
        status=status,
        include_system=include_system,
        oauth_missing=oauth_missing,
        calendar_missing=calendar_missing,
        inactive_days_gt=inactive_days_gt,
        test_only=test_only,
    )




@app.get("/admin/ui/test-accounts/preflight-delete")
async def admin_ui_test_accounts_preflight_delete(request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    test_specialist_filter = (
        Specialist.is_test.is_(True),
        Specialist.is_system.is_(False),
    )

    async with async_session_factory() as session:
        test_specialists = int(
            (await session.execute(select(func.count()).select_from(Specialist).where(*test_specialist_filter))).scalar_one()
        )

        clients = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(Client)
                    .join(Specialist, Specialist.specialist_id == Client.specialist_id)
                    .where(*test_specialist_filter)
                )
            ).scalar_one()
        )

        appointments = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(Appointment)
                    .join(Specialist, Specialist.specialist_id == Appointment.specialist_id)
                    .where(*test_specialist_filter)
                )
            ).scalar_one()
        )

    return {
        "test_specialists": test_specialists,
        "clients": clients,
        "appointments": appointments,
    }


@app.post("/admin/ui/diagnostics/run")
async def admin_ui_run_diagnostic(payload: AdminDiagnosticRunRequest, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        result = await _execute_diagnostic(payload.check_type)
        return {
            "status": "completed",
            "summary": result["summary"],
            "findings": result["findings"],
        }
    except Exception as exc:
        logger.exception("event=admin_diagnostic_run_failed check_type=%s", payload.check_type)
        return {
            "status": "failed",
            "summary": {
                "scanned": 0,
                "findings_total": 1,
                "high": 1,
                "medium": 0,
                "low": 0,
            },
            "findings": [
            {
                "severity": "high",
                "code": "DIAGNOSTIC_JOB_FAILED",
                "entity_ref": payload.check_type,
                "message": f"Diagnostic failed: {exc.__class__.__name__}",
                "recommended_action": "Check server logs and retry",
            }
            ],
        }


@app.post("/admin/ui/test-accounts/delete-all")
async def admin_ui_test_accounts_delete_all(
    payload: AdminBulkDeleteAllRequest,
    request: Request,
):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    if payload.confirmation_phrase != BULK_DELETE_TEST_ACCOUNTS_CONFIRMATION_PHRASE:
        raise HTTPException(status_code=400, detail="INVALID_CONFIRMATION_PHRASE")

    async with async_session_factory() as session:
        job = AdminBulkCleanupJob(
            status="pending",
            total_specialists=0,
            processed_specialists=0,
            error_count=0,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    return {
        "job_id": str(job.job_id),
        "status": job.status,
    }


@app.get("/admin/ui/specialists/{specialist_id}")
async def admin_ui_specialist_detail(
    specialist_id: str,
    request: Request,
    include_system: bool = Query(default=False),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    logger.info(
        "event=admin_ui_specialist_detail_access request_id=%s specialist_id=%s",
        _request_id_from_request(request),
        specialist_id,
    )

    payload = await build_admin_specialist_detail_payload(
        specialist_uuid,
        include_system=include_system,
    )
    if payload is None:
        _raise_not_found()

    return payload


@app.get("/admin/ui/specialists/{specialist_id}/delete-test/preflight")
async def admin_ui_delete_test_specialist_preflight(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        if specialist.is_system:
            raise HTTPException(status_code=403, detail="FORBIDDEN_SYSTEM")

        if not specialist.is_test:
            raise HTTPException(status_code=403, detail="FORBIDDEN_NOT_TEST")

        clients_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(Client).where(Client.specialist_id == specialist_uuid)
                )
            ).scalar_one()
        )
        appointments_count = int(
            (
                await session.execute(
                    select(func.count()).select_from(Appointment).where(Appointment.specialist_id == specialist_uuid)
                )
            ).scalar_one()
        )
        media_count = int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(SpecialistPublicMedia)
                    .join(SpecialistPublicProfile, SpecialistPublicMedia.profile_id == SpecialistPublicProfile.id)
                    .where(SpecialistPublicProfile.specialist_id == specialist_uuid)
                )
            ).scalar_one()
        )

    return {
        "specialist_id": str(specialist_uuid),
        "eligible": True,
        "counts": {
            "clients": clients_count,
            "appointments": appointments_count,
            "media": media_count,
        },
    }


@app.post("/admin/ui/specialists/{specialist_id}/reset-test-data")
async def admin_ui_reset_test_specialist_data(
    specialist_id: str,
    payload: AdminResetTestDataRequest,
    request: Request,
):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    request_id = _request_id_from_request(request)

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        if specialist.is_system:
            if payload.step == "preflight":
                await write_admin_audit_log(
                    session,
                    request_id=request_id,
                    admin_subject="cookie_session",
                    action="reset_test_data_preflight_requested",
                    target_type="specialist",
                    target_id=specialist_uuid,
                    success=False,
                    payload={},
                    error_code="FORBIDDEN_SYSTEM",
                    error_message="Cannot reset runtime data for system specialist",
                )
                await session.commit()
            raise HTTPException(status_code=403, detail="FORBIDDEN_SYSTEM")

        if not specialist.is_test:
            if payload.step == "preflight":
                await write_admin_audit_log(
                    session,
                    request_id=request_id,
                    admin_subject="cookie_session",
                    action="reset_test_data_preflight_requested",
                    target_type="specialist",
                    target_id=specialist_uuid,
                    success=False,
                    payload={},
                    error_code="FORBIDDEN_NOT_TEST",
                    error_message="Reset is allowed only for test specialists",
                )
                await session.commit()
            raise HTTPException(status_code=403, detail="FORBIDDEN_NOT_TEST")

        if payload.step == "preflight":
            counts = await _count_reset_test_data(session, specialist_uuid)
            token, expires_at = _issue_reset_token(specialist_uuid)
            response_payload = {
                "ok": True,
                "specialist_id": str(specialist_uuid),
                "flow_step": "preflight",
                "eligible": True,
                "delete_counts": counts,
                "confirmation_token": token,
                "confirmation_phrase": _reset_confirmation_phrase(specialist_uuid),
                "expires_in_sec": RESET_TEST_DATA_CONFIRMATION_TTL_SECONDS,
                "expires_at": expires_at.isoformat(),
            }
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="reset_test_data_preflight_requested",
                target_type="specialist",
                target_id=specialist_uuid,
                success=True,
                payload={"delete_counts": counts},
            )
            await session.commit()
            return response_payload

        if payload.step == "confirm":
            if not payload.confirmation_token:
                raise HTTPException(status_code=400, detail="CONFIRMATION_TOKEN_REQUIRED")
            expected_phrase = _reset_confirmation_phrase(specialist_uuid)
            if payload.confirmation_phrase != expected_phrase:
                raise HTTPException(status_code=422, detail="VALIDATION")
            token_state = _get_reset_token_state(payload.confirmation_token)
            if not token_state or token_state.get("specialist_id") != specialist_uuid:
                raise HTTPException(status_code=409, detail="PRECONDITION_FAILED")
            if not _set_reset_token_confirmed(payload.confirmation_token):
                raise HTTPException(status_code=409, detail="PRECONDITION_FAILED")
            return {
                "ok": True,
                "specialist_id": str(specialist_uuid),
                "flow_step": "confirmation",
                "confirmed": True,
            }

        if payload.step != "execute":
            raise HTTPException(status_code=400, detail="UNKNOWN_STEP")

        if not payload.confirmation_token:
            raise HTTPException(status_code=400, detail="CONFIRMATION_TOKEN_REQUIRED")

        if payload.confirmation_phrase != _reset_confirmation_phrase(specialist_uuid):
            raise HTTPException(status_code=422, detail="VALIDATION")

        if not _consume_reset_token(payload.confirmation_token, specialist_uuid):
            raise HTTPException(status_code=409, detail="PRECONDITION_FAILED")

        planned_counts = await _count_reset_test_data(session, specialist_uuid)

        await write_admin_audit_log(
            session,
            request_id=request_id,
            admin_subject="cookie_session",
            action="reset_test_data_execute_requested",
            target_type="specialist",
            target_id=specialist_uuid,
            success=True,
            payload={"planned_delete_counts": planned_counts},
        )
        await session.commit()

        try:
            async with session.begin():
                deleted_counts = await _delete_reset_test_data_runtime_rows(session, specialist_uuid)

                await write_admin_audit_log(
                    session,
                    request_id=request_id,
                    admin_subject="cookie_session",
                    action="reset_test_data_committed",
                    target_type="specialist",
                    target_id=specialist_uuid,
                    success=True,
                    payload={"deleted_counts": deleted_counts},
                )

            _cleanup_reset_tokens_for_specialist(specialist_uuid)
            return {
                "ok": True,
                "specialist_id": str(specialist_uuid),
                "status": "reset_completed",
                "deleted_counts": deleted_counts,
            }
        except Exception as exc:
            await session.rollback()
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="reset_test_data_rolled_back",
                target_type="specialist",
                target_id=specialist_uuid,
                success=False,
                payload={"planned_delete_counts": planned_counts},
                error_code="RESET_TEST_DATA_FAILED",
                error_message=str(exc),
            )
            await session.commit()
            raise HTTPException(status_code=500, detail="RESET_TEST_DATA_FAILED") from exc


@app.post("/admin/ui/specialists/{specialist_id}/delete-test")
async def admin_ui_delete_test_specialist(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    deleted_counts = {
        "appointments": 0,
        "clients": 0,
        "media": 0,
        "oauth_tokens": 0,
        "specialist": 0,
    }

    media_file_keys: list[str] = []
    async with async_session_factory() as session:
        async with session.begin():
            specialist = await session.get(Specialist, specialist_uuid)
            if specialist is None:
                _raise_not_found()

            if specialist.is_system:
                raise HTTPException(status_code=403, detail="FORBIDDEN_SYSTEM")

            if not specialist.is_test:
                raise HTTPException(status_code=403, detail="FORBIDDEN_NOT_TEST")

            deleted_appointments = await session.execute(
                delete(Appointment).where(Appointment.specialist_id == specialist_uuid)
            )
            deleted_counts["appointments"] = int(deleted_appointments.rowcount or 0)

            deleted_clients = await session.execute(
                delete(Client).where(Client.specialist_id == specialist_uuid)
            )
            deleted_counts["clients"] = int(deleted_clients.rowcount or 0)

            media_rows = (
                await session.execute(
                    text(
                        """
                        SELECT m.file_key
                        FROM specialist_public_media m
                        JOIN specialist_public_profile p ON p.id = m.profile_id
                        WHERE p.specialist_id = :sid
                        """
                    ),
                    {"sid": str(specialist_uuid)},
                )
            ).scalars().all()
            media_file_keys = [str(key) for key in media_rows if key]
            deleted_media = await session.execute(
                text(
                    """
                    DELETE FROM specialist_public_media
                    WHERE profile_id IN (
                      SELECT id FROM specialist_public_profile WHERE specialist_id = :sid
                    )
                    """
                ),
                {"sid": str(specialist_uuid)},
            )
            deleted_counts["media"] = int(deleted_media.rowcount or 0)

            deleted_oauth = await session.execute(
                delete(GoogleOAuth).where(GoogleOAuth.specialist_id == specialist_uuid)
            )
            deleted_counts["oauth_tokens"] = int(deleted_oauth.rowcount or 0)

            deleted_specialist = await session.execute(
                delete(Specialist).where(Specialist.specialist_id == specialist_uuid)
            )
            deleted_counts["specialist"] = int(deleted_specialist.rowcount or 0)

            if deleted_counts["specialist"] == 0:
                _raise_not_found()

    for file_key in media_file_keys:
        remove_file_if_exists(uploads_root=Path(config.PROFILE_UPLOADS_DIR), file_key=file_key)

    _schedule_storage_cleanup(
        {
            "specialist_id": str(specialist_uuid),
            "deleted_counts": deleted_counts,
        }
    )

    return {
        "status": "deleted",
        "deleted_counts": deleted_counts,
    }


@app.post("/admin/ui/specialists/{specialist_id}/disable")
async def admin_ui_disable_specialist(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    request_id = _request_id_from_request(request)

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        old_status = specialist.status.value
        payload = {"old_status": old_status, "new_status": "disabled"}

        if specialist.is_system:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="disable_specialist",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload=payload,
                error_code="FORBIDDEN_SYSTEM",
                error_message="Cannot disable system specialist",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot disable system specialist")

        if not specialist.is_test:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="disable_specialist",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload=payload,
                error_code="FORBIDDEN_NOT_TEST",
                error_message="Destructive action allowed only for test specialists",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot disable non-test specialist")

        if specialist.status != SpecialistStatus.suspended:
            specialist.status = SpecialistStatus.suspended

        await write_admin_audit_log(
            session,
            request_id=request_id,
            admin_subject="cookie_session",
            action="disable_specialist",
            target_type="specialist",
            target_id=specialist.specialist_id,
            success=True,
            payload=payload,
        )
        await session.commit()

    return {"ok": True, "specialist_id": str(specialist_uuid), "status": "disabled"}




@app.post("/admin/ui/specialists/{specialist_id}/enable")
async def admin_ui_enable_specialist(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    request_id = _request_id_from_request(request)

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        old_status = specialist.status.value

        if specialist.status == SpecialistStatus.suspended:
            specialist.status = SpecialistStatus.active

        payload = {"old_status": old_status, "new_status": specialist.status.value}

        await write_admin_audit_log(
            session,
            request_id=request_id,
            admin_subject="cookie_session",
            action="enable_specialist",
            target_type="specialist",
            target_id=specialist.specialist_id,
            success=True,
            payload=payload,
        )
        await session.commit()

    return {"ok": True, "specialist_id": str(specialist_uuid), "status": specialist.status.value}




@app.post("/admin/ui/specialists/{specialist_id}/reset-oauth")
async def admin_ui_reset_specialist_oauth(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    request_id = _request_id_from_request(request)

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        if specialist.is_system:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="reset_oauth",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload={"deleted_rows": 0},
                error_code="FORBIDDEN_SYSTEM",
                error_message="Cannot reset oauth for system specialist",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot reset oauth for system specialist")

        if not specialist.is_test:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="reset_oauth",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload={"deleted_rows": 0},
                error_code="FORBIDDEN_NOT_TEST",
                error_message="Destructive action allowed only for test specialists",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot reset oauth for non-test specialist")

        result = await session.execute(
            delete(GoogleOAuth).where(GoogleOAuth.specialist_id == specialist.specialist_id)
        )
        deleted_rows = int(result.rowcount or 0)

        await write_admin_audit_log(
            session,
            request_id=request_id,
            admin_subject="cookie_session",
            action="reset_oauth",
            target_type="specialist",
            target_id=specialist.specialist_id,
            success=True,
            payload={"deleted_rows": deleted_rows},
        )
        await session.commit()

    return {"ok": True, "specialist_id": str(specialist_uuid), "oauth_connected": False}




@app.post("/admin/ui/specialists/{specialist_id}/tariff")
async def admin_ui_change_specialist_tariff(specialist_id: str, request: Request):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    try:
        specialist_uuid = uuid.UUID(specialist_id)
    except ValueError:
        _raise_not_found()

    request_id = _request_id_from_request(request)

    try:
        body = await request.json()
    except Exception:
        body = {}

    raw_tariff_plan = body.get("tariff_plan") if isinstance(body, dict) else None
    allowed_tariff_values = {plan.value for plan in TariffPlan}

    async with async_session_factory() as session:
        specialist = await session.get(Specialist, specialist_uuid)
        if specialist is None:
            _raise_not_found()

        if specialist.is_system:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="change_tariff",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload={"old_tariff": None, "new_tariff": raw_tariff_plan},
                error_code="FORBIDDEN_SYSTEM",
                error_message="Cannot change tariff for system specialist",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot change tariff for system specialist")

        if not specialist.is_test:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="change_tariff",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload={"old_tariff": None, "new_tariff": raw_tariff_plan},
                error_code="FORBIDDEN_NOT_TEST",
                error_message="Destructive action allowed only for test specialists",
            )
            await session.commit()
            raise HTTPException(status_code=403, detail="Cannot change tariff for non-test specialist")

        profile = await session.get(SpecialistProfile, specialist.specialist_id)
        if profile is None:
            profile = SpecialistProfile(
                specialist_id=specialist.specialist_id,
                public_name=str(specialist.specialist_id),
                owner_tg_user_id=0,
                specialist_timezone="UTC",
            )
            session.add(profile)
            await session.flush()

        old_tariff = profile.tariff_plan.value if profile.tariff_plan else None

        if not isinstance(raw_tariff_plan, str) or raw_tariff_plan not in allowed_tariff_values:
            await write_admin_audit_log(
                session,
                request_id=request_id,
                admin_subject="cookie_session",
                action="change_tariff",
                target_type="specialist",
                target_id=specialist.specialist_id,
                success=False,
                payload={"old_tariff": old_tariff, "new_tariff": raw_tariff_plan},
                error_code="VALIDATION",
                error_message="Invalid tariff plan",
            )
            await session.commit()
            raise HTTPException(status_code=422, detail="Invalid tariff_plan")

        profile.tariff_plan = TariffPlan(raw_tariff_plan)

        await write_admin_audit_log(
            session,
            request_id=request_id,
            admin_subject="cookie_session",
            action="change_tariff",
            target_type="specialist",
            target_id=specialist.specialist_id,
            success=True,
            payload={
                "old_tariff": old_tariff,
                "new_tariff": profile.tariff_plan.value if profile.tariff_plan else raw_tariff_plan,
            },
        )
        await session.commit()

    return {
        "ok": True,
        "specialist_id": str(specialist_uuid),
        "tariff_plan": profile.tariff_plan.value if profile.tariff_plan else raw_tariff_plan,
    }


@app.get("/admin/ui/logs")
async def admin_ui_logs(
    request: Request,
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0, ge=0),
    bot_id: int | None = Query(default=None),
    specialist_id: str | None = Query(default=None),
    tg_user_id: int | None = Query(default=None),
    direction: LogDirection | None = Query(default=None),
    is_error: bool | None = Query(default=None),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    stmt, limit_value = build_message_log_query(
        since=since,
        until=until,
        limit=limit,
        offset=offset,
        bot_id=bot_id,
        specialist_id=specialist_id,
        tg_user_id=tg_user_id,
        direction=direction,
        is_error=is_error,
    )

    logger.info(
        "event=admin_query request_id=%s path=/admin/ui/logs tg_user_id=%s is_error=%s created_at_since=%s created_at_until=%s limit=%s offset=%s",
        _request_id_from_request(request),
        tg_user_id,
        is_error,
        since,
        until,
        limit_value,
        offset,
    )

    async with async_session_factory() as session:
        result = await session.execute(stmt)
        items = [serialize_message_log(row, redact=True) for row in result.scalars().all()]

    return {"items": items, "limit": limit_value, "offset": offset}


@app.get("/admin/ui/audit-log")
async def admin_ui_audit_log(
    request: Request,
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    success: bool | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0, ge=0),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    since_dt = parse_iso_datetime(since) if since else None
    until_dt = parse_iso_datetime(until) if until else None

    target_uuid: uuid.UUID | None = None
    if target_id is not None:
        try:
            target_uuid = uuid.UUID(target_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid UUID format") from exc

    limit_value = clamp_limit(limit)

    stmt = build_admin_audit_log_query(
        since=since_dt,
        until=until_dt,
        action=action,
        target_type=target_type,
        target_id=target_uuid,
        success=success,
    ).limit(limit_value).offset(offset)

    logger.info(
        "event=admin_query request_id=%s path=/admin/ui/audit-log action=%s target_type=%s target_id=%s success=%s created_at_since=%s created_at_until=%s limit=%s offset=%s",
        _request_id_from_request(request),
        action,
        target_type,
        target_id,
        success,
        since,
        until,
        limit_value,
        offset,
    )

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    items = [
        {
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": str(row.target_id),
            "success": bool(row.success),
            "payload": sanitize_admin_audit_payload_for_ui(row.payload_json or {}),
            "error_code": row.error_code,
            "error_message": row.error_message,
        }
        for row in rows
    ]

    return {"items": items, "limit": limit_value, "offset": offset}


@app.get("/admin/ui/heartbeats")
async def admin_ui_heartbeats(
    request: Request,
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int | None = Query(default=100),
    offset: int = Query(default=0, ge=0),
    service_name: str | None = Query(default=None),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    stmt, limit_value = build_heartbeat_query(
        since=since,
        until=until,
        limit=limit,
        offset=offset,
        service_name=service_name,
    )

    logger.info(
        "event=admin_query request_id=%s path=/admin/ui/heartbeats service_name=%s created_at_since=%s created_at_until=%s limit=%s offset=%s",
        _request_id_from_request(request),
        service_name,
        since,
        until,
        limit_value,
        offset,
    )

    async with async_session_factory() as session:
        result = await session.execute(stmt)
        items = [serialize_service_heartbeat(row) for row in result.scalars().all()]

    return {"items": items, "limit": limit_value, "offset": offset}


@app.get("/admin/ui/overview")
async def admin_ui_overview(
    request: Request,
    include_system: bool = Query(default=False),
):
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    env_name = config.APP_ENV or os.getenv("ENV") or "unknown"
    version = os.getenv("BUILD_VERSION") or os.getenv("GIT_SHA") or "unknown"

    logger.info(
        "event=admin_ui_overview_access request_id=%s path=/admin/ui/overview env=%s",
        _request_id_from_request(request),
        env_name,
    )

    async with async_session_factory() as session:
        payload = await compute_admin_overview(session, include_system=include_system)

    payload["env"] = env_name
    payload["version"] = version
    return payload


@app.get("/admin", response_class=HTMLResponse)
async def admin_console_entry(request: Request) -> HTMLResponse:
    if not _admin_ui_enabled():
        _raise_not_found()

    cookie_value = request.cookies.get(ADMIN_UI_COOKIE_NAME, "")
    if not admin_ui_session.verify_admin_session_cookie(cookie_value):
        _raise_not_found()

    version = os.getenv("BUILD_VERSION") or os.getenv("GIT_SHA") or "unknown"
    env_name = config.APP_ENV or os.getenv("ENV") or "unknown"
    server_time_utc = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    logger.info(
        "event=admin_console_access request_id=%s path=/admin env=%s",
        _request_id_from_request(request),
        env_name,
    )

    return HTMLResponse(
        content=f"""
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; background:#f6f8fb; color:#1f2937; margin:0; }}
    .container {{ max-width:1200px; margin:24px auto; padding:0 16px; }}
    .header {{ background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; margin-bottom:16px; }}
    .meta {{ color:#6b7280; font-size:14px; margin:4px 0; }}
    .tabs {{ display:flex; gap:8px; margin:12px 0 20px; flex-wrap:wrap; }}
    .tabs a {{ text-decoration:none; padding:8px 12px; border:1px solid #d1d5db; border-radius:8px; background:#fff; color:#111827; }}
    .section {{ background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; margin-bottom:16px; }}
    .filters {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }}
    .filters input, .filters select {{ padding:6px 8px; border:1px solid #d1d5db; border-radius:6px; }}
    .btn {{ padding:7px 12px; border:1px solid #2563eb; background:#2563eb; color:#fff; border-radius:6px; cursor:pointer; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border:1px solid #e5e7eb; padding:8px; text-align:left; font-size:14px; vertical-align:top; }}
    th {{ background:#f9fafb; }}
    .state {{ color:#6b7280; }}
    .hidden {{ display:none; }}
    .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }}
    .pill.ok {{ background:#dcfce7; color:#166534; }}
    .pill.err {{ background:#fee2e2; color:#991b1b; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:700; margin-right:6px; }}
    .badge-test {{ background:#ffedd5; color:#c2410c; border:1px solid #fdba74; }}
    .badge-system {{ background:#e5e7eb; color:#374151; border:1px solid #d1d5db; }}
  </style>
</head>
<body>
  <div class='container'>
    <header class='header'>
      <h1>Zumbot Admin Console</h1>
      <p class='meta'>Environment: {env_name}</p>
      <p class='meta'>Server time (UTC): {server_time_utc}</p>
      <p class='meta'>Version: {version}</p>
      <button id='logout-btn' class='btn' type='button'>Logout</button>
      <nav class='tabs'>
        <a href='#overview'>Overview</a>
        <a href='#specialists'>Specialists</a>
        <a href='#logs'>Logs</a>
        <a href='#heartbeats'>Heartbeats</a>
        <a href='#audit-log'>Audit Log</a>
      </nav>
    </header>

    <section id='overview' class='section'>
      <h2>Overview</h2>
      <div id='admin-overview' class='state'>Loading overview…</div>
    </section>

    <section id='specialists' class='section'>
      <h2>Specialists</h2>
      <div class='filters'>
        <label for='status-filter'>Status</label>
        <select id='status-filter'>
          <option value=''>All</option>
          <option value='onboarding'>onboarding</option>
          <option value='active'>active</option>
          <option value='suspended'>suspended</option>
        </select>
        <label for='include-system-filter'>include_system</label><input id='include-system-filter' type='checkbox' />
        <label for='oauth-missing-filter'>oauth_missing</label><input id='oauth-missing-filter' type='checkbox' />
        <label for='calendar-missing-filter'>calendar_missing</label><input id='calendar-missing-filter' type='checkbox' />
        <label for='inactive-days-filter'>inactive_days_gt</label><input id='inactive-days-filter' type='number' min='1' step='1' style='width:90px;' />
        <label for='test-only-filter'>test_only</label><input id='test-only-filter' type='checkbox' />
        <button id='apply-filter' class='btn' type='button'>Apply</button>
      </div>
      <p id='specialists-state' class='state'>Загрузка...</p>
      <table id='specialists-table' class='hidden'>
        <thead><tr><th>Имя</th><th>Flags</th><th>Статус</th><th>Timezone</th><th>Onboarding</th><th>OAuth</th><th>Calendar</th><th>Active_7d</th><th>Клиенты</th><th>Тариф</th><th>Последняя активность</th></tr></thead>
        <tbody></tbody>
      </table>
    </section>

    <section id='logs' class='section'>
      <h2>Logs</h2>
      <div class='filters'>
        <input id='logs-since' placeholder='since (ISO)' />
        <input id='logs-until' placeholder='until (ISO)' />
        <input id='logs-bot-id' placeholder='bot_id' />
        <input id='logs-specialist-id' placeholder='specialist_id' />
        <input id='logs-tg-user-id' placeholder='tg_user_id' />
        <select id='logs-direction'><option value=''>direction</option><option value='IN'>IN</option><option value='OUT'>OUT</option></select>
        <select id='logs-is-error'><option value=''>is_error</option><option value='true'>true</option><option value='false'>false</option></select>
        <input id='logs-limit' value='100' style='width:70px;' />
        <input id='logs-offset' value='0' style='width:70px;' />
        <button id='logs-apply' class='btn' type='button'>Apply</button>
      </div>
      <p id='logs-state' class='state'>Loading...</p>
      <table id='logs-table' class='hidden'>
        <thead><tr><th>created_at</th><th>is_error</th><th>direction</th><th>bot_id</th><th>specialist_id</th><th>tg_user_id</th><th>message_type</th><th>content</th><th>request_id</th></tr></thead>
        <tbody></tbody>
      </table>
    </section>


    <section id='audit-log' class='section'>
      <h2>Audit Log</h2>
      <div class='filters'>
        <input id='audit-since' placeholder='since (ISO)' />
        <input id='audit-until' placeholder='until (ISO)' />
        <input id='audit-action' placeholder='action' />
        <select id='audit-success'><option value=''>success</option><option value='true'>true</option><option value='false'>false</option></select>
        <label for='audit-limit'>limit</label>
        <select id='audit-limit'><option value='50'>50</option><option value='100' selected>100</option><option value='200'>200</option></select>
        <button id='audit-apply' class='btn' type='button'>Apply</button>
      </div>
      <div class='filters'>
        <button id='audit-prev' class='btn' type='button'>Prev</button>
        <button id='audit-next' class='btn' type='button'>Next</button>
        <span id='audit-page' class='state'>offset: 0</span>
      </div>
      <p id='audit-log-state' class='state'>Loading...</p>
      <div id='audit-log-section'>
        <table id='audit-log-table' class='hidden'>
          <thead><tr><th>Time</th><th>Action</th><th>Target</th><th>Success</th><th>Payload</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>

    <section id='heartbeats' class='section'>
      <h2>Heartbeats</h2>
      <div class='filters'>
        <input id='hb-since' placeholder='since (ISO)' />
        <input id='hb-until' placeholder='until (ISO)' />
        <input id='hb-service-name' placeholder='service_name' />
        <input id='hb-limit' value='100' style='width:70px;' />
        <input id='hb-offset' value='0' style='width:70px;' />
        <button id='hb-apply' class='btn' type='button'>Apply</button>
      </div>
      <p id='hb-state' class='state'>Loading...</p>
      <table id='hb-table' class='hidden'>
        <thead><tr><th>created_at</th><th>service_name</th><th>status</th><th>details</th></tr></thead>
        <tbody></tbody>
      </table>
    </section>

  </div>

  <script>
    const overviewEl=document.getElementById('admin-overview');
    const stateEl=document.getElementById('specialists-state');
    const tableEl=document.getElementById('specialists-table');
    const tbodyEl=tableEl.querySelector('tbody');
    const statusEl=document.getElementById('status-filter');
    const buttonEl=document.getElementById('apply-filter');
    const includeSystemEl=document.getElementById('include-system-filter');
    const oauthMissingEl=document.getElementById('oauth-missing-filter');
    const calendarMissingEl=document.getElementById('calendar-missing-filter');
    const inactiveDaysEl=document.getElementById('inactive-days-filter');
    const testOnlyEl=document.getElementById('test-only-filter');

    const logsStateEl=document.getElementById('logs-state');
    const logsTableEl=document.getElementById('logs-table');
    const logsBodyEl=logsTableEl.querySelector('tbody');

    const hbStateEl=document.getElementById('hb-state');
    const hbTableEl=document.getElementById('hb-table');
    const hbBodyEl=hbTableEl.querySelector('tbody');

    const auditStateEl=document.getElementById('audit-log-state');
    const auditSectionEl=document.getElementById('audit-log-section');
    const auditTableEl=document.getElementById('audit-log-table');
    const auditBodyEl=auditTableEl.querySelector('tbody');
    const auditLimitEl=document.getElementById('audit-limit');
    const auditPageEl=document.getElementById('audit-page');
    const auditPrevEl=document.getElementById('audit-prev');
    const auditNextEl=document.getElementById('audit-next');
    let auditOffset=0;
    let auditLastItemsCount=0;

    const logoutButtonEl=document.getElementById('logout-btn');

    async function logout(){{
      try {{
        await fetch('/admin/logout', {{ method:'POST' }});
      }} finally {{
        window.location.href='/admin/login';
      }}
    }}
    logoutButtonEl.addEventListener('click', logout);

    function setOverviewLoading(){{overviewEl.textContent='Loading overview…';}}
    function setOverviewError(){{overviewEl.textContent='Failed to load overview';}}
    function renderOverview(payload){{overviewEl.innerHTML='<ul>'
      +'<li>specialists_total: '+String(payload.specialists_total??0)+'</li>'
      +'<li>specialists_active_7d: '+String(payload.specialists_active_7d??0)+'</li>'
      +'<li>clients_total: '+String(payload.clients_total??0)+'</li>'
      +'<li>errors_24h: '+String(payload.errors_24h??0)+'</li>'
      +'</ul>';}}

    function getIncludeSystemParam(){{return includeSystemEl.checked?'1':'0';}}
    async function loadOverview(){{
      setOverviewLoading();
      const params=new URLSearchParams({{include_system:getIncludeSystemParam()}});
      const url='/admin/ui/overview?'+params.toString();
      try{{const res=await fetch(url,{{credentials:'same-origin'}});if(!res.ok)throw new Error('HTTP '+res.status);renderOverview(await res.json());}}
      catch(_err){{setOverviewError();}}
    }}

    function setState(state,msg){{
      if(state==='loading'){{stateEl.textContent='Загрузка...';stateEl.style.display='block';tableEl.classList.add('hidden');}}
      else if(state==='empty'){{stateEl.textContent='Данных нет';stateEl.style.display='block';tableEl.classList.add('hidden');}}
      else if(state==='error'){{stateEl.textContent=msg||'Ошибка загрузки';stateEl.style.display='block';tableEl.classList.add('hidden');}}
      else{{stateEl.style.display='none';tableEl.classList.remove('hidden');}}
    }}

    function renderRows(items){{tbodyEl.innerHTML='';items.forEach((item)=>{{const row=document.createElement('tr');
      const onboarding=(item.onboarding_master_done?'M✓':'M—')+' '+(item.onboarding_personal_done?'P✓':'P—');
      const oauth=item.oauth_connected?'connected':'missing';
      const calendar=item.calendar_selected?'selected':'missing';
      const active=item.active_7d?'yes':'no';
      const timezone=item.timezone||'—';
      const lastActivity=item.last_activity_at||'—';
      const flags=[];
      if(item.is_test)flags.push('<span class="badge badge-test" title="Test specialist. Used for admin test-account workflows.">TEST</span>');
      if(item.is_system)flags.push('<span class="badge badge-system" title="System account. Protected from destructive admin operations.">SYSTEM</span>');
      const flagsCell=flags.length?flags.join(' '):'—';
      row.innerHTML='<td>'+((item.public_name||''))+'</td><td>'+flagsCell+'</td><td>'+((item.status||''))+'</td><td>'+timezone+'</td><td>'+onboarding+'</td><td>'+oauth+'</td><td>'+calendar+'</td><td>'+active+'</td><td>'+String(item.clients_count??0)+'</td><td>'+((item.tariff_plan||''))+'</td><td>'+lastActivity+'</td>';
      tbodyEl.appendChild(row);}});}}

    async function loadSpecialists(){{
      setState('loading');
      const status=statusEl.value;
      const params=new URLSearchParams({{limit:'100',offset:'0',include_system:getIncludeSystemParam()}});
      if(status)params.set('status',status);
      if(oauthMissingEl.checked)params.set('oauth_missing','1');
      if(calendarMissingEl.checked)params.set('calendar_missing','1');
      if(testOnlyEl.checked)params.set('test_only','1');
      const inactiveDaysRaw=(inactiveDaysEl.value||'').trim(); if(inactiveDaysRaw)params.set('inactive_days_gt',inactiveDaysRaw);
      try{{const res=await fetch('/admin/ui/specialists?'+params.toString(),{{credentials:'same-origin'}}); if(!res.ok)throw new Error('HTTP '+res.status);
        const payload=await res.json(); const items=payload.items||[]; if(items.length===0){{setState('empty');return;}} renderRows(items); setState('ready');}}
      catch(_err){{setState('error','Не удалось загрузить список специалистов');}}
    }}

    function setLogsState(kind,msg){{
      if(kind==='loading'){{logsStateEl.textContent='Loading logs...';logsStateEl.style.display='block';logsTableEl.classList.add('hidden');return;}}
      if(kind==='empty'){{logsStateEl.textContent='No logs found';logsStateEl.style.display='block';logsTableEl.classList.add('hidden');return;}}
      if(kind==='error'){{logsStateEl.textContent=msg;logsStateEl.style.display='block';logsTableEl.classList.add('hidden');return;}}
      logsStateEl.style.display='none';logsTableEl.classList.remove('hidden');
    }}

    function renderLogs(items){{logsBodyEl.innerHTML='';items.forEach((item)=>{{const row=document.createElement('tr');
      row.innerHTML='<td>'+(item.created_at||'—')+'</td><td>'+(item.is_error?'true':'false')+'</td><td>'+(item.direction||'—')+'</td><td>'+(item.bot_id??'—')+'</td><td>'+(item.specialist_id||'—')+'</td><td>'+(item.tg_user_id??'—')+'</td><td>'+(item.message_type||'—')+'</td><td>'+(item.content||'—')+'</td><td>'+(item.request_id||'—')+'</td>';
      logsBodyEl.appendChild(row);}});}}

    async function loadLogs(){{
      setLogsState('loading');
      const params=new URLSearchParams();
      const map=[['since','logs-since'],['until','logs-until'],['bot_id','logs-bot-id'],['specialist_id','logs-specialist-id'],['tg_user_id','logs-tg-user-id'],['direction','logs-direction'],['is_error','logs-is-error'],['limit','logs-limit'],['offset','logs-offset']];
      map.forEach(([k,id])=>{{const v=(document.getElementById(id).value||'').trim(); if(v)params.set(k,v);}});
      try{{const res=await fetch('/admin/ui/logs?'+params.toString(),{{credentials:'same-origin'}});
        if(res.status===404){{setLogsState('error','Not available');return;}}
        if(!res.ok)throw new Error('HTTP '+res.status);
        const payload=await res.json(); const items=payload.items||[]; if(items.length===0){{setLogsState('empty');return;}} renderLogs(items); setLogsState('ready');}}
      catch(_err){{setLogsState('error','Failed to load logs');}}
    }}


    function setAuditPaginationState(){{
      const limitValue=parseInt(auditLimitEl.value||'100',10)||100;
      auditPageEl.textContent='offset: '+String(auditOffset)+' · limit: '+String(limitValue);
      auditPrevEl.disabled=auditOffset<=0;
      auditNextEl.disabled=auditLastItemsCount<limitValue;
    }}

    function setAuditState(kind,msg){{
      if(kind==='loading'){{auditStateEl.textContent='Loading audit log...';auditStateEl.style.display='block';auditTableEl.classList.add('hidden');setAuditPaginationState();return;}}
      if(kind==='empty'){{auditStateEl.textContent='No audit records';auditStateEl.style.display='block';auditTableEl.classList.add('hidden');setAuditPaginationState();return;}}
      if(kind==='error'){{auditStateEl.textContent=msg;auditStateEl.style.display='block';auditTableEl.classList.add('hidden');setAuditPaginationState();return;}}
      auditStateEl.style.display='none';auditTableEl.classList.remove('hidden');setAuditPaginationState();
    }}

    function renderAuditLogs(items){{auditBodyEl.innerHTML='';items.forEach((item)=>{{const row=document.createElement('tr');
      const target=(item.target_type||'—')+' / '+(item.target_id||'—');
      const success=item.success===true?'true':'false';
      const payload=item.payload?JSON.stringify(item.payload):'{{}}';
      row.innerHTML='<td>'+(item.created_at||'—')+'</td><td>'+(item.action||'—')+'</td><td>'+target+'</td><td>'+success+'</td><td><pre style="margin:0;white-space:pre-wrap;">'+payload+'</pre></td>';
      auditBodyEl.appendChild(row);}});}}

    async function loadAuditLog(){{
      setAuditState('loading');
      const params=new URLSearchParams();
      [['since','audit-since'],['until','audit-until'],['action','audit-action'],['success','audit-success']].forEach(([k,id])=>{{const v=(document.getElementById(id).value||'').trim(); if(v)params.set(k,v);}});
      const limitValue=(auditLimitEl.value||'100').trim()||'100';
      params.set('limit',limitValue);
      params.set('offset',String(auditOffset));
      try{{const res=await fetch('/admin/ui/audit-log?'+params.toString(),{{credentials:'same-origin'}});
        if(res.status===404){{auditLastItemsCount=0;setAuditState('error','Not available');return;}}
        if(!res.ok)throw new Error('HTTP '+res.status);
        const payload=await res.json();
        const items=payload.items||[];
        auditLastItemsCount=items.length;
        if(items.length===0){{setAuditState('empty');return;}}
        renderAuditLogs(items);
        setAuditState('ready');
      }}
      catch(_err){{auditLastItemsCount=0;setAuditState('error','Failed to load audit log');}}
    }}

    function resetAuditPaginationAndReload(){{
      auditOffset=0;
      loadAuditLog();
    }}

    function setHbState(kind,msg){{
      if(kind==='loading'){{hbStateEl.textContent='Loading heartbeats...';hbStateEl.style.display='block';hbTableEl.classList.add('hidden');return;}}
      if(kind==='empty'){{hbStateEl.textContent='No heartbeats found';hbStateEl.style.display='block';hbTableEl.classList.add('hidden');return;}}
      if(kind==='error'){{hbStateEl.textContent=msg;hbStateEl.style.display='block';hbTableEl.classList.add('hidden');return;}}
      hbStateEl.style.display='none';hbTableEl.classList.remove('hidden');
    }}

    function renderHeartbeats(items){{hbBodyEl.innerHTML='';items.forEach((item)=>{{const row=document.createElement('tr');
      const ok=((item.db_ok===true)&&(item.loop_ok===true));
      const status=ok?"<span class='pill ok'>ok</span>":"<span class='pill err'>issue</span>";
      row.innerHTML='<td>'+(item.timestamp||item.created_at||'—')+'</td><td>'+(item.service_name||'—')+'</td><td>'+status+'</td><td>'+(item.details||'—')+'</td>';
      hbBodyEl.appendChild(row);}});}}

    async function loadHeartbeats(){{
      setHbState('loading');
      const params=new URLSearchParams();
      [['since','hb-since'],['until','hb-until'],['service_name','hb-service-name'],['limit','hb-limit'],['offset','hb-offset']].forEach(([k,id])=>{{const v=(document.getElementById(id).value||'').trim(); if(v)params.set(k,v);}});
      try{{const res=await fetch('/admin/ui/heartbeats?'+params.toString(),{{credentials:'same-origin'}});
        if(res.status===404){{setHbState('error','Not available');return;}}
        if(!res.ok)throw new Error('HTTP '+res.status);
        const payload=await res.json(); const items=payload.items||[]; if(items.length===0){{setHbState('empty');return;}} renderHeartbeats(items); setHbState('ready');}}
      catch(_err){{setHbState('error','Failed to load heartbeats');}}
    }}

    buttonEl.addEventListener('click',()=>{{loadOverview();loadSpecialists();}});
    includeSystemEl.addEventListener('change',()=>{{loadOverview();loadSpecialists();}});
    document.getElementById('logs-apply').addEventListener('click',loadLogs);
    document.getElementById('hb-apply').addEventListener('click',loadHeartbeats);
    document.getElementById('audit-apply').addEventListener('click',resetAuditPaginationAndReload);
    document.getElementById('audit-since').addEventListener('change',resetAuditPaginationAndReload);
    document.getElementById('audit-until').addEventListener('change',resetAuditPaginationAndReload);
    document.getElementById('audit-action').addEventListener('change',resetAuditPaginationAndReload);
    document.getElementById('audit-success').addEventListener('change',resetAuditPaginationAndReload);
    document.getElementById('audit-limit').addEventListener('change',resetAuditPaginationAndReload);
    auditPrevEl.addEventListener('click',()=>{{
      const limitValue=parseInt(auditLimitEl.value||'100',10)||100;
      auditOffset=Math.max(0,auditOffset-limitValue);
      loadAuditLog();
    }});
    auditNextEl.addEventListener('click',()=>{{
      const limitValue=parseInt(auditLimitEl.value||'100',10)||100;
      auditOffset=auditOffset+limitValue;
      loadAuditLog();
    }});

    setAuditPaginationState();
    loadOverview();
    loadSpecialists();
    loadLogs();
    loadHeartbeats();
    loadAuditLog();
  </script>
</body>
</html>
""",
        status_code=200,
    )
async def readyz():
    start_time = time.perf_counter()

    db_ok = False
    error_short = ""
    try:
        async with async_session_factory() as session:
            await asyncio.wait_for(
                session.execute(select(1)),
                timeout=READYZ_DB_TIMEOUT_SEC,
            )
        db_ok = True
    except Exception as exc:
        error_short = type(exc).__name__

    now = time.monotonic()
    loop_ok = (now - heartbeat.LAST_TICK_TS) < READYZ_LOOP_TIMEOUT_SEC

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    db_status = "ok" if db_ok else "fail"
    loop_status = "ok" if loop_ok else "fail"
    if not (db_ok and loop_ok):
        logger.warning(
            "event=readyz_check_error request_id=%s db_ok=%s loop_ok=%s latency_ms=%s",
            get_request_id(),
            db_ok,
            loop_ok,
            latency_ms,
        )

    await _write_service_heartbeat(
        db_ok=db_ok,
        loop_ok=loop_ok,
        latency_ms=latency_ms,
        details=error_short or None,
    )

    if db_ok and loop_ok:
        return {"status": "ready", "db": "ok", "loop": "ok"}

    response = {"status": "not_ready", "db": db_status, "loop": loop_status}
    if not db_ok and error_short:
        response["error"] = error_short
    return JSONResponse(
        status_code=503,
        content=response,
    )


if config.ENABLE_READYZ:
    app.add_api_route("/readyz", readyz, methods=["GET"])


@app.post("/integrations/google-calendar/webhook")
async def google_calendar_webhook(request: Request, background_tasks: BackgroundTasks):
    headers = request.headers
    channel_id = headers.get("X-Goog-Channel-Id")
    resource_id = headers.get("X-Goog-Resource-Id")
    resource_state = headers.get("X-Goog-Resource-State")
    message_number = headers.get("X-Goog-Message-Number")

    if not channel_id or not resource_id or not resource_state:
        logger.warning(
            "event=google_calendar_webhook_missing_headers request_id=%s channel_id=%s resource_id=%s resource_state=%s message_number=%s",
            _request_id_from_request(request),
            channel_id,
            resource_id,
            resource_state,
            message_number,
        )
        return Response(status_code=200)

    async with async_session_factory() as session:
        sync_state = (
            await session.execute(
                select(
                    CalendarSyncState.specialist_id,
                    CalendarSyncState.calendar_id,
                    CalendarSyncState.last_enqueued_at,
                ).where(CalendarSyncState.channel_id == channel_id)
            )
        ).first()

        if sync_state is None:
            should_log, suppressed_count = _should_log_unknown_channel(channel_id)
            if should_log:
                logger.info(
                    "event=google_calendar_webhook_unknown_channel request_id=%s channel_id=%s resource_id=%s resource_state=%s message_number=%s suppressed_in_window=%s",
                    _request_id_from_request(request),
                    channel_id,
                    resource_id,
                    resource_state,
                    message_number,
                    suppressed_count,
                )
            return Response(status_code=200)

        specialist_id, calendar_id, last_enqueued_at = sync_state
        now = datetime.now(timezone.utc)
        throttle_window_start = now - timedelta(seconds=GOOGLE_CALENDAR_REVERSE_SYNC_THROTTLE_SECONDS)
        if last_enqueued_at is not None and last_enqueued_at >= throttle_window_start:
            logger.info(
                "event=reverse_sync_skipped_throttle request_id=%s channel_id=%s specialist_id=%s calendar_id=%s resource_state=%s message_number=%s last_enqueued_at=%s",
                _request_id_from_request(request),
                channel_id,
                specialist_id,
                calendar_id,
                resource_state,
                message_number,
                last_enqueued_at.isoformat(),
            )
            return Response(status_code=200)

        await session.execute(
            update(CalendarSyncState)
            .where(
                CalendarSyncState.specialist_id == specialist_id,
                CalendarSyncState.calendar_id == calendar_id,
            )
            .values(last_enqueued_at=now)
        )
        await session.commit()

    background_tasks.add_task(run_calendar_reverse_sync, specialist_id, calendar_id)
    logger.info(
        "event=google_calendar_webhook_enqueued request_id=%s channel_id=%s specialist_id=%s calendar_id=%s resource_state=%s message_number=%s",
        _request_id_from_request(request),
        channel_id,
        specialist_id,
        calendar_id,
        resource_state,
        message_number,
    )
    return Response(status_code=200)


@app.get("/site-health")
async def site_health() -> PlainTextResponse:
    return PlainTextResponse("ok")


class TelegramConsumeRequest(BaseModel):
    token: str


class ContactFormRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    message: str = Field(min_length=1, max_length=4000)
    hp: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("invalid email")
        return email


def _send_contact_email_smtp(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_from: str,
    smtp_to: str,
    smtp_timeout_seconds: int,
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> None:
    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = smtp_to
    message["Subject"] = subject
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    if smtp_port == 465:
        smtp_client = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=smtp_timeout_seconds)
    else:
        smtp_client = smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout_seconds)

    with smtp_client as smtp:
        smtp.ehlo()
        if smtp_port != 465:
            try:
                smtp.starttls()
            except smtplib.SMTPNotSupportedError:
                pass
            else:
                smtp.ehlo()
        smtp.login(smtp_user, smtp_password)
        smtp.sendmail(smtp_from, [smtp_to], message.as_string())


@app.post("/public/contact")
async def public_contact(request: Request) -> JSONResponse:
    request_id = _request_id_from_request(request)

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=200, content={"ok": False, "error": "invalid_json"})

    try:
        form = ContactFormRequest.model_validate(payload)
    except ValidationError:
        return JSONResponse(status_code=200, content={"ok": False, "error": "validation_error"})

    logger.info(
        "event=contact_form_received request_id=%s name_len=%s email_len=%s message_len=%s hp_len=%s",
        request_id,
        len(form.name),
        len(str(form.email)),
        len(form.message),
        len(form.hp or ""),
    )

    if form.hp and form.hp.strip():
        return JSONResponse(status_code=200, content={"ok": True})

    smtp_host = os.getenv("CONTACT_SMTP_HOST", "").strip()
    smtp_port_raw = os.getenv("CONTACT_SMTP_PORT", "587").strip()
    smtp_user = os.getenv("CONTACT_SMTP_USER", "").strip()
    smtp_password = os.getenv("CONTACT_SMTP_PASSWORD", "").strip()
    smtp_from = os.getenv("CONTACT_FROM_EMAIL", os.getenv("CONTACT_SMTP_FROM", smtp_user)).strip()
    smtp_to = os.getenv("CONTACT_TO_EMAIL", os.getenv("CONTACT_SMTP_TO", "info@zumbot.ru")).strip()
    smtp_timeout_raw = os.getenv("CONTACT_SMTP_TIMEOUT_SECONDS", "10").strip()

    required_env = {
        "CONTACT_SMTP_HOST": smtp_host,
        "CONTACT_SMTP_USER": smtp_user,
        "CONTACT_SMTP_PASSWORD": smtp_password,
    }
    missing_required_env = [key for key, value in required_env.items() if not value]
    if missing_required_env:
        await notify_exception(
            where="web.contact_form",
            exc=RuntimeError("smtp_not_configured"),
            context={
                "request_id": request_id,
                "missing_required_env": ",".join(missing_required_env),
                "name_len": len(form.name),
                "email_len": len(str(form.email)),
                "message_len": len(form.message),
            },
        )
        return JSONResponse(status_code=200, content={"ok": False, "error": "smtp_not_configured"})

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        await notify_exception(
            where="web.contact_form",
            exc=RuntimeError("smtp_invalid_port"),
            context={"request_id": request_id},
        )
        return JSONResponse(status_code=200, content={"ok": False, "error": "smtp_not_configured"})

    try:
        smtp_timeout_seconds = int(smtp_timeout_raw)
    except ValueError:
        smtp_timeout_seconds = 10

    if smtp_timeout_seconds <= 0:
        smtp_timeout_seconds = 10

    logger.info(
        "event=contact_form_smtp_attempt request_id=%s host=%s port=%s timeout=%s",
        request_id,
        smtp_host,
        smtp_port,
        smtp_timeout_seconds,
    )

    subject = f"Zumbot contact form: {form.name} {form.email}"
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    body = (
        f"name: {form.name}\n"
        f"email: {form.email}\n"
        f"message:\n{form.message}\n\n"
        f"timestamp_utc: {timestamp_utc}\n"
        f"request_id: {request_id}\n"
    )

    try:
        await asyncio.to_thread(
            _send_contact_email_smtp,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_from=smtp_from,
            smtp_to=smtp_to,
            smtp_timeout_seconds=smtp_timeout_seconds,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        await notify_exception(
            where="web.contact_form",
            exc=RuntimeError("smtp_send_failed"),
            context={
                "request_id": request_id,
                "error": type(exc).__name__,
                "message": str(exc),
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "timeout": smtp_timeout_seconds,
            },
        )
        return JSONResponse(status_code=200, content={"ok": False, "error": "smtp_send_failed"})

    contact_autoreply_enabled = os.getenv("CONTACT_AUTOREPLY_ENABLED", "true").strip().lower() != "false"

    if contact_autoreply_enabled and "@" in form.email:
        autoreply_subject = "Мы получили ваше сообщение — Zumbot"
        autoreply_body = (
            f"Здравствуйте, {form.name}!\n\n"
            "Мы получили ваше сообщение:\n\n"
            "-----------------------\n"
            f"{form.message}\n"
            "-----------------------\n\n"
            f"Номер обращения: {request_id}\n\n"
            "Мы свяжемся с вами в ближайшее время.\n\n"
            "С уважением,\n"
            "Команда Zumbot\n"
            "https://zumbot.ru\n"
        )
        try:
            await asyncio.to_thread(
                _send_contact_email_smtp,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_from=smtp_from,
                smtp_to=form.email,
                smtp_timeout_seconds=smtp_timeout_seconds,
                subject=autoreply_subject,
                body=autoreply_body,
                reply_to=smtp_from,
            )
        except Exception as exc:
            await notify_exception(
                where="web.contact_form_autoreply",
                exc=RuntimeError("smtp_send_failed"),
                context={
                    "request_id": request_id,
                    "error": type(exc).__name__,
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "timeout": smtp_timeout_seconds,
                },
            )

    return JSONResponse(status_code=200, content={"ok": True})


@app.post("/auth/telegram/consume")
async def consume_telegram_connect_token(payload: TelegramConsumeRequest) -> JSONResponse:
    token = payload.token.strip()
    if not token:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "token_required"},
        )

    async with async_session_factory() as session:
        consumed = await web_connect.consume_connect_token(session, token)
        if consumed is None:
            await session.rollback()
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "expired_or_used"},
            )

        specialist_id, tg_user_id = consumed
        await session.commit()

    session_cookie = web_session.sign_session_cookie(specialist_id, tg_user_id)
    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        key=config.WEB_CONNECT_COOKIE_NAME,
        value=session_cookie,
        httponly=True,
        secure=True,
        samesite="Lax",
        path="/",
    )
    return response


@app.get("/connect")
async def connect_page() -> HTMLResponse:
    html = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Подключение Google Календаря</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f5f7fb; color: #1f2937; }
    main { max-width: 640px; margin: 32px auto; background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 8px 28px rgba(15,23,42,.08); }
    h1 { margin-top: 0; font-size: 28px; }
    p { line-height: 1.5; }
    ul { margin: 8px 0 12px; padding-left: 22px; line-height: 1.5; }
    button { border: 0; border-radius: 10px; background: #2563eb; color: #fff; font-size: 16px; font-weight: 600; padding: 12px 20px; cursor: pointer; }
    button:disabled { background: #94a3b8; cursor: not-allowed; }
    .hint { color: #475569; font-size: 14px; }
    .warn { margin: 16px 0; border-radius: 8px; padding: 12px; background: #fff7ed; border: 1px solid #fdba74; }
  </style>
</head>
<body>
  <main>
    <h1>Подключение Google Календаря</h1>
    <p>Для работы записи клиентов необходимо подключить ваш Google Календарь.</p>
    <p>Вы будете перенаправлены на страницу Google для безопасной авторизации.<br />
    Zumbot получит доступ только к выбранному календарю, чтобы:</p>
    <ul>
      <li>показывать доступные слоты для записи</li>
      <li>создавать события при бронировании</li>
      <li>отменять события при отмене записи</li>
    </ul>
    <p>Мы не получаем доступ к вашей почте или другим данным Google.</p>
    <p class="hint">Авторизация откроется в стандартной странице Google (не во встроенном iframe).</p>
    <div id="webview-warning" class="warn" hidden>Откройте в браузере (Safari/Chrome), иначе Google может блокировать вход.</div>
    <form action="/google/oauth/start" method="post">
      <label class="hint" style="display:block; margin: 0 0 12px;">
        <input id="consent-checkbox" type="checkbox" required style="margin-right: 8px;" />
        Продолжая, вы подтверждаете согласие с <a href="/terms-ru" target="_blank" rel="noopener">Публичной офертой</a> и <a href="/privacy-ru" target="_blank" rel="noopener">Политикой конфиденциальности</a>.
      </label>
      <button id="google-connect-btn" type="submit" disabled>Подключить Google</button>
    </form>
  </main>
  <script>
    (function () {
      const button = document.getElementById('google-connect-btn');
      const consentCheckbox = document.getElementById('consent-checkbox');
      const warning = document.getElementById('webview-warning');
      const ua = navigator.userAgent || '';
      let isAuthorized = false;
      if (ua.includes('Telegram') || ua.includes('WebView')) {
        warning.hidden = false;
      }

      const hash = window.location.hash || '';
      const params = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : hash);
      const token = params.get('token') || params.get('t');

      function updateButtonState() {
        button.disabled = !(isAuthorized && consentCheckbox.checked);
      }

      function clearHash() {
        if (window.location.hash) {
          history.replaceState(null, '', window.location.pathname + window.location.search);
        }
      }

      async function checkStatus() {
        try {
          const res = await fetch('/connect/status', { credentials: 'same-origin' });
          if (!res.ok) return false;
          const data = await res.json();
          return !!data.ok;
        } catch (_) {
          return false;
        }
      }

      async function consumeConnectToken(rawToken) {
        try {
          const res = await fetch('/auth/telegram/consume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ token: rawToken }),
          });
          if (!res.ok) return false;
          const data = await res.json();
          return !!data.ok;
        } catch (_) {
          return false;
        }
      }

      async function init() {
        if (token) {
          const consumed = await consumeConnectToken(token);
          if (consumed) {
            clearHash();
            isAuthorized = true;
            updateButtonState();
            return;
          }
        }

        const sessionOk = await checkStatus();
        if (sessionOk) {
          isAuthorized = true;
          updateButtonState();
        }
      }

      consentCheckbox.addEventListener('change', updateButtonState);
      updateButtonState();
      init();
    })();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/connect/status")
async def connect_status(request: Request) -> JSONResponse:
    cookie_value = request.cookies.get(config.WEB_CONNECT_COOKIE_NAME, "")
    session = web_session.verify_session_cookie(cookie_value)
    return JSONResponse(content={"ok": session is not None})




@app.get("/analytics/summary")
async def analytics_summary(request: Request) -> JSONResponse:
    cookie_value = request.cookies.get(config.WEB_CONNECT_COOKIE_NAME, "")
    verified_session = web_session.verify_session_cookie(cookie_value)
    if not verified_session:
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})

    specialist_id, _tg_user_id = verified_session

    async with async_session_factory() as session:
        profile = await session.get(SpecialistProfile, specialist_id)
        if profile is None:
            return JSONResponse(status_code=404, content={"detail": "specialist_not_found"})

        try:
            ensure_analytics_access(getattr(profile, "tariff_plan", None))
        except AnalyticsAccessError:
            return JSONResponse(status_code=403, content={"detail": ANALYTICS_PRO_REQUIRED_ERROR})

        total = await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.specialist_id == specialist_id)
        )
        confirmed = await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.specialist_id == specialist_id)
            .where(Appointment.booking_state == BookingState.confirmed)
        )
        canceled = await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.specialist_id == specialist_id)
            .where(Appointment.booking_state.in_((BookingState.canceled_by_client, BookingState.canceled_by_specialist)))
        )

    return JSONResponse(
        status_code=200,
        content={
            "total_bookings": int(total or 0),
            "confirmed": int(confirmed or 0),
            "canceled": int(canceled or 0),
        },
    )

@app.post("/google/oauth/start")
async def google_oauth_start(request: Request) -> Response:
    cookie_value = request.cookies.get(config.WEB_CONNECT_COOKIE_NAME, "")
    verified_session = web_session.verify_session_cookie(cookie_value)
    if verified_session is None:
        return HTMLResponse(
            content="Сессия не найдена. Вернитесь в Telegram и откройте ссылку заново.",
            status_code=200,
        )

    specialist_id, _tg_user_id = verified_session
    async with async_session_factory() as session:
        oauth_state = await create_oauth_state(session, specialist_id, OAuthStateType.google_connect)
        await session.commit()

    response = RedirectResponse(url=get_auth_url(oauth_state), status_code=302)
    response.headers["Cache-Control"] = "no-store"
    return response


async def _write_service_heartbeat(
    db_ok: bool,
    loop_ok: bool,
    latency_ms: int,
    details: str | None,
) -> None:
    global LAST_HEARTBEAT_WRITE_TS

    now = time.monotonic()
    time_since_last = now - LAST_HEARTBEAT_WRITE_TS
    if time_since_last < HEARTBEAT_WRITE_INTERVAL_SEC:
        logger.debug(
            "readyz heartbeat skipped due to throttling time_since_last=%.2fs",
            time_since_last,
        )
        return

    async with HEARTBEAT_WRITE_LOCK:
        now = time.monotonic()
        time_since_last = now - LAST_HEARTBEAT_WRITE_TS
        if time_since_last < HEARTBEAT_WRITE_INTERVAL_SEC:
            logger.debug(
                "readyz heartbeat skipped due to throttling time_since_last=%.2fs",
                time_since_last,
            )
            return

        try:
            async with async_session_factory() as session:
                session.add(
                    ServiceHeartbeat(
                        service_name=SERVICE_NAME,
                        db_ok=db_ok,
                        loop_ok=loop_ok,
                        latency_ms=latency_ms,
                        details=details,
                    )
                )
                await session.commit()
            LAST_HEARTBEAT_WRITE_TS = now
            logger.debug(
                "readyz heartbeat stored db_ok=%s loop_ok=%s latency_ms=%s",
                db_ok,
                loop_ok,
                latency_ms,
            )
        except Exception:
            logger.warning("readyz heartbeat write failed", exc_info=True)



async def _read_request_body_with_limit(request: Request, max_bytes: int) -> bytes | None:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/tg/webhook/{bot_id}/{secret}")
async def telegram_personal_webhook(bot_id: int, secret: str, request: Request):
    """Receive updates for personal specialist bots (webhook mode)."""
    request_id = _request_id_from_request(request)
    started = time.perf_counter()
    content_type = request.headers.get("content-type")
    content_length_header = request.headers.get("content-length")
    request_body: bytes | None = None

    if content_length_header:
        try:
            content_length = int(content_length_header)
            if content_length > MAX_WEBHOOK_BODY_BYTES:
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
                    request_id,
                    bot_id,
                    "PayloadTooLarge",
                    duration_ms,
                )
                return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
        except ValueError:
            request_body = await _read_request_body_with_limit(request, MAX_WEBHOOK_BODY_BYTES)
            if request_body is None:
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
                    request_id,
                    bot_id,
                    "PayloadTooLarge",
                    duration_ms,
                )
                return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
    else:
        request_body = await _read_request_body_with_limit(request, MAX_WEBHOOK_BODY_BYTES)
        if request_body is None:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
                request_id,
                bot_id,
                "PayloadTooLarge",
                duration_ms,
            )
            return JSONResponse(status_code=413, content={"detail": "payload_too_large"})

    body_size_bytes = len(request_body) if request_body is not None else int(content_length_header or 0)

    try:
        if request_body is None:
            raw_update = await request.json()
        else:
            raw_update = json.loads(request_body)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
            request_id,
            bot_id,
            type(exc).__name__,
            duration_ms,
        )
        return Response(status_code=200)

    async with async_session_factory() as session:
        stmt = select(TelegramBot).where(
            TelegramBot.bot_user_id == bot_id,
            TelegramBot.webhook_secret == secret,
            TelegramBot.status == TelegramBotStatus.active,
        )
        tg_bot = (await session.execute(stmt)).scalar_one_or_none()

    if tg_bot is None:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
            request_id,
            bot_id,
            "WebhookAuthFailed",
            duration_ms,
        )
        return JSONResponse(status_code=404, content={"detail": "not_found"})

    status_code = 200
    try:
        await process_update(tg_bot, raw_update)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "event=tg_webhook_error request_id=%s bot_id=%s exception_class=%s duration_ms=%s",
            request_id,
            bot_id,
            type(exc).__name__,
            duration_ms,
        )
        await notify_exception(
            where="web_server.telegram_personal_webhook",
            exc=exc,
            context={
                "bot_id": bot_id,
                "specialist_id": str(tg_bot.specialist_id),
                "request_id": request_id,
            },
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "event=tg_webhook_in request_id=%s bot_id=%s body_size_bytes=%s content_type=%s duration_ms=%s status_code=%s",
        request_id,
        bot_id,
        body_size_bytes,
        content_type,
        duration_ms,
        status_code,
    )
    return Response(status_code=status_code)

@app.get("/google/oauth/callback")
async def google_oauth_callback(request: Request):
    request_id = _request_id_from_request(request)
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        logger.warning(
            "event=google_oauth_callback request_id=%s stage=%s outcome=%s",
            request_id,
            "state_validate",
            "error",
        )
        return f"<h1>Ошибка авторизации: {error}</h1>"

    if not code or not state:
        logger.warning(
            "event=google_oauth_callback request_id=%s stage=%s outcome=%s",
            request_id,
            "state_validate",
            "error",
        )
        return "<h1>Ошибка: Отсутствуют обязательные параметры (code, state)</h1>"

    try:
        async with async_session_factory() as session:
            state_stmt = select(OAuthState).where(OAuthState.state == state)
            oauth_state = (await session.execute(state_stmt)).scalar_one_or_none()

            if oauth_state is None:
                logger.warning(
                    "event=google_oauth_callback request_id=%s stage=%s outcome=%s",
                    request_id,
                    "state_validate",
                    "error",
                )
                return "<h1>Ошибка: state не найден или уже использован.</h1>"

            now_utc = datetime.now(timezone.utc)
            expires_at = oauth_state.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now_utc:
                await session.delete(oauth_state)
                await session.commit()
                logger.warning(
                    "event=google_oauth_callback request_id=%s stage=%s outcome=%s",
                    request_id,
                    "state_validate",
                    "error",
                )
                return "<h1>Ошибка: state истёк. Запросите новую ссылку из Telegram.</h1>"

            if oauth_state.type not in {OAuthStateType.google_connect, OAuthStateType.google_reconnect}:
                await session.delete(oauth_state)
                await session.commit()
                logger.warning(
                    "event=google_oauth_callback request_id=%s stage=%s outcome=%s",
                    request_id,
                    "state_validate",
                    "error",
                )
                return "<h1>Ошибка: Некорректный тип OAuth state.</h1>"

            specialist_id = oauth_state.specialist_id
            logger.info(
                "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s",
                request_id,
                "state_validate",
                "ok",
                specialist_id,
            )

        try:
            refresh_token, _access_token, credentials = await exchange_code_for_token_async(code)
            logger.info(
                "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s",
                request_id,
                "token_exchange",
                "ok",
                specialist_id,
            )
        except asyncio.TimeoutError as exc:
            logger.exception(
                "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s exception_class=%s",
                request_id,
                "token_exchange",
                "error",
                specialist_id,
                type(exc).__name__,
            )
            text_out = "<h1>Ошибка: timeout при обмене кода Google OAuth. Повторите попытку.</h1>"
            await notify_exception(
                where="web_server.google_oauth_callback.token_exchange",
                exc=exc,
                context={"specialist_id": str(specialist_id), "request_id": request_id},
                user_visible_text=text_out,
                stage="google_oauth",
            )
            return text_out
        except requests.exceptions.RequestException as exc:
            logger.exception(
                "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s exception_class=%s",
                request_id,
                "token_exchange",
                "error",
                specialist_id,
                type(exc).__name__,
            )
            text_out = "<h1>Ошибка: network error при обмене кода Google OAuth. Повторите попытку.</h1>"
            await notify_exception(
                where="web_server.google_oauth_callback.token_exchange",
                exc=exc,
                context={"specialist_id": str(specialist_id), "request_id": request_id},
                user_visible_text=text_out,
                stage="google_oauth",
            )
            return text_out

        async with async_session_factory() as session:
            stmt = select(GoogleOAuth).where(GoogleOAuth.specialist_id == specialist_id)
            oauth_entry = (await session.execute(stmt)).scalar_one_or_none()

            if not refresh_token:
                if oauth_entry and oauth_entry.refresh_token_encrypted:
                    oauth_entry.status = GoogleOAuthStatus.connected
                    oauth_entry.token_updated_at = datetime.now(timezone.utc)
                    oauth_entry.scopes = scopes_as_string()
                    logger.info(
                        "OAuth callback without refresh_token; reusing existing token specialist_id=%s",
                        specialist_id,
                    )
                else:
                    if oauth_entry:
                        oauth_entry.status = GoogleOAuthStatus.error
                        oauth_entry.scopes = scopes_as_string()
                        oauth_entry.token_updated_at = datetime.now(timezone.utc)
                    logger.warning(
                        "OAuth callback missing refresh_token and no stored token specialist_id=%s",
                        specialist_id,
                    )

                    auth_data = (
                        await session.execute(
                            select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.specialist_id == specialist_id)
                        )
                    ).scalar_one_or_none()
                    await session.commit()

                    reconnect_message = (
                        "⚠️ Не удалось получить постоянный доступ к Google Calendar.\n"
                        "Переподключите аккаунт через master bot: нужен offline-доступ и подтверждение consent."
                    )
                    if auth_data and bot is not None:
                        try:
                            await bot.send_message(chat_id=auth_data.tg_user_id, text=reconnect_message)
                        except Exception:
                            logger.warning(
                                "Failed to send oauth reconnect instructions specialist_id=%s",
                                specialist_id,
                                exc_info=True,
                            )

                    logger.warning(
                        "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s",
                        request_id,
                        "db_update",
                        "error",
                        specialist_id,
                    )
                    return """
                    <html>
                        <head><title>Google Calendar reconnect required</title></head>
                        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                            <h1 style="color: #c62828;">Требуется переподключение</h1>
                            <p>Google не вернул refresh_token (постоянный доступ).</p>
                            <p>Вернитесь в Telegram и переподключите аккаунт с подтверждением доступа.</p>
                        </body>
                    </html>
                    """
            else:
                encrypted_refresh_token = encrypt_token(refresh_token)
                if oauth_entry:
                    oauth_entry.refresh_token_encrypted = encrypted_refresh_token
                    oauth_entry.status = GoogleOAuthStatus.connected
                    oauth_entry.token_updated_at = datetime.now(timezone.utc)
                    oauth_entry.scopes = scopes_as_string()
                else:
                    session.add(
                        GoogleOAuth(
                            specialist_id=specialist_id,
                            refresh_token_encrypted=encrypted_refresh_token,
                            scopes=scopes_as_string(),
                            status=GoogleOAuthStatus.connected,
                            token_updated_at=datetime.now(timezone.utc),
                        )
                    )

            auth_data = (
                await session.execute(
                    select(SpecialistAuthTelegram).where(SpecialistAuthTelegram.specialist_id == specialist_id)
                )
            ).scalar_one_or_none()
            profile = (
                await session.execute(
                    select(SpecialistProfile).where(SpecialistProfile.specialist_id == specialist_id)
                )
            ).scalar_one_or_none()
            specialist_name = profile.public_name if profile else "Unknown"

            state_entry = (
                await session.execute(
                    select(OAuthState).where(OAuthState.state == state)
                )
            ).scalar_one_or_none()
            if state_entry is not None:
                await session.delete(state_entry)

            await process_referral_activation(session, specialist_id)
            await session.commit()

            permissions_ok = True
            granted_scopes = set()
            raw_scopes = getattr(credentials, "scopes", None)
            if isinstance(raw_scopes, (list, tuple, set)):
                granted_scopes = set(raw_scopes)

            missing_scopes = set(required_scopes()) - granted_scopes if granted_scopes else set()
            if missing_scopes:
                permissions_ok = False
                logger.warning(
                    "Google connected but OAuth scope set is incomplete specialist_id=%s missing_scopes=%s",
                    specialist_id,
                    sorted(missing_scopes),
                )

            try:
                await list_calendars(specialist_id)
            except GoogleCalendarInsufficientPermissionsError:
                permissions_ok = False
                logger.warning("Google connected but insufficient permissions specialist_id=%s", specialist_id)

            if auth_data and bot is not None:
                if permissions_ok:
                    text_out = "✅ **Google подключен!**\n\nШаг 4 из 4: выберите рабочий календарь в master bot."
                    reply_markup = build_calendar_switch_keyboard(has_selected_calendar=False)
                else:
                    text_out = (
                        "⚠️ Google подключен, но доступов недостаточно для просмотра календарей и выбора рабочего календаря.\n"
                        "Переподключите через /start и подтвердите права: просмотр календарей и управление событиями."
                    )
                    reply_markup = None
                try:
                    await bot.send_message(chat_id=auth_data.tg_user_id, text=text_out, reply_markup=reply_markup)
                    await log_outbound_message(
                        bot=bot,
                        tg_user_id=auth_data.tg_user_id,
                        content=text_out,
                        fsm_state="google_connected_callback",
                        specialist_name=specialist_name,
                        user_handle=f"@{auth_data.tg_username}" if auth_data.tg_username else str(auth_data.tg_user_id),
                    )
                except Exception:
                    logger.warning("Failed to send TG notification specialist_id=%s", specialist_id, exc_info=True)

        logger.info(
            "event=google_oauth_callback request_id=%s stage=%s outcome=%s specialist_id=%s",
            request_id,
            "db_update",
            "ok",
            specialist_id,
        )

        return RedirectResponse(url=f"{config.PUBLIC_SITE_URL}/success", status_code=302)

    except Exception as exc:
        logger.exception(
            "event=google_oauth_callback request_id=%s stage=%s outcome=%s exception_class=%s",
            request_id,
            "db_update",
            "error",
            type(exc).__name__,
        )
        text_out = "<h1>Произошла ошибка при подключении Google. Попробуйте ещё раз из Telegram.</h1>"
        await notify_exception(
            where="web_server.google_oauth_callback",
            exc=exc,
            context={"request_id": request_id},
            user_visible_text=text_out,
            stage="google_oauth",
        )
        return text_out


@app.get("/{public_slug}")
async def site_public_specialist_slug(public_slug: str) -> HTMLResponse:
    route_name = resolve_frontend_route(f"/{public_slug}")
    if route_name != "specialist_profile_page":
        raise HTTPException(status_code=404, detail="Not Found")

    if not (ASSETS_DIR.exists() and INDEX_FILE.exists()):
        raise HTTPException(status_code=404, detail="Not Found")

    html = """<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Профиль специалиста — Zumbot</title>
    <link rel="icon" href="/assets/icons/favicon.ico" sizes="any" />
    <link rel="icon" type="image/png" sizes="32x32" href="/assets/icons/favicon-32.png" />
    <link rel="icon" type="image/png" sizes="16x16" href="/assets/icons/favicon-16.png" />
    <link rel="stylesheet" href="/assets/styles.css" />
    <link rel="stylesheet" href="/assets/specialist.css" />
  </head>
  <body>
    <main id="specialist-page" class="specialist-page specialist-page--hidden" aria-live="polite">
      <header id="specialist-sticky-header" class="specialist-header" aria-label="Specialist profile header">
        <div class="specialist-header__inner container">
          <div class="specialist-header__identity">
            <p id="public-specialist-display-name" class="specialist-header__display-name"></p>
            <p id="public-specialist-specialization" class="specialist-header__specialization"></p>
          </div>
          <div class="specialist-header__actions">
            <a
              id="specialist-header-book-link"
              class="specialist-button specialist-button--primary specialist-header__book-button specialist-hidden"
              href="#"
              target="_blank"
              rel="noopener noreferrer"
            >
              Записаться
            </a>
          </div>
        </div>
      </header>

      <section id="hero" class="specialist-page__section specialist-page__section--hero section" aria-label="Hero специалиста">
        <div class="container">
          <div id="public-specialist-hero-grid" class="section-card specialist-hero hero-grid specialist-card">
            <div id="public-specialist-hero-photo" class="specialist-hero__photo-wrap profile-photo">
              <div id="public-specialist-hero-photo-fallback" class="specialist-hero__photo-placeholder" aria-label="Фото специалиста недоступно">
                <span class="specialist-hero__photo-placeholder-icon" aria-hidden="true">⊚</span>
                <p class="specialist-hero__photo-placeholder-title">Фото скоро появится</p>
                <p class="specialist-hero__photo-placeholder-text">Пока можно познакомиться с профилем специалиста.</p>
              </div>
              <img id="public-specialist-hero-photo-image" class="specialist-hero__photo specialist-hidden" alt="Фото специалиста" />
            </div>
            <div class="specialist-hero__content">
              <p class="specialist-hero__kicker"></p>
              <h1 id="public-specialist-hero-name" class="specialist-hero__title hero-name"></h1>
              <p id="public-specialist-hero-specialization" class="specialist-hero__subtitle hero-specialization"></p>
              <blockquote id="public-specialist-hero-quote" class="specialist-hero__quote hero-quote specialist-hidden"></blockquote>
              <ul id="specialist-contacts" class="specialist-contacts specialist-hidden" aria-label="Контакты специалиста"></ul>
              <div class="specialist-hero__actions hero-cta">
                <a id="specialist-contact-link" href="#booking" class="specialist-button specialist-button--primary hero-button">Связаться со специалистом</a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <nav id="specialist-section-nav" class="specialist-subnav" aria-label="Навигация по разделам специалиста">
        <div class="container specialist-subnav__inner">
          <div class="specialist-subnav__list" role="tablist" aria-label="Разделы страницы">
            <div class="specialist-subnav__item" role="presentation"><a href="#about" data-section-id="about" class="specialist-subnav__link" role="tab">О себе</a></div>
            <div class="specialist-subnav__item" role="presentation"><a href="#education" data-section-id="education" class="specialist-subnav__link" role="tab">Образование</a></div>
            <div class="specialist-subnav__item" role="presentation"><a href="#documents" data-section-id="documents" class="specialist-subnav__link" role="tab">Документы</a></div>
            <div class="specialist-subnav__item" role="presentation"><a href="#services" data-section-id="services" class="specialist-subnav__link" role="tab">Услуги и цены</a></div>
            <div class="specialist-subnav__item" role="presentation"><a href="#reviews" data-section-id="reviews" class="specialist-subnav__link" role="tab">Отзывы</a></div>
          </div>
        </div>
      </nav>
      <section id="about" class="specialist-page__section section" aria-label="О себе"><div class="container"><div class="section-card specialist-card specialist-content-card"><h2 class="section-title specialist-section-title">О себе</h2><div id="specialist-about-content" class="section-text specialist-rich-text"></div></div></div></section>
      <section id="education" class="specialist-page__section section" aria-label="Образование"><div class="container"><div class="section-card specialist-card specialist-content-card"><h2 class="section-title specialist-section-title">Образование</h2><div id="specialist-education-content"></div></div></div></section>
      <section id="documents" class="specialist-page__section section" aria-label="Документы"><div class="container"><div class="section-card specialist-card specialist-content-card"><h2 class="section-title specialist-section-title">Документы</h2><div id="specialist-documents-content"></div></div></div></section>
      <section id="services" class="specialist-page__section section" aria-label="Услуги и цены"><div class="container"><div class="section-card specialist-card specialist-content-card"><h2 class="section-title specialist-section-title">Услуги и цены</h2><div id="specialist-services-content"></div></div></div></section>
      <section id="reviews" class="specialist-page__section section" aria-label="Отзывы"><div class="container"><div class="section-card specialist-card specialist-content-card"><h2 class="section-title specialist-section-title">Отзывы</h2><div id="specialist-reviews-content"></div></div></div></section>
      <section id="booking" class="specialist-page__section section" aria-label="Запись на консультацию"><div class="container"><div class="section-card specialist-card specialist-cta-card cta-final"><h2 class="section-title specialist-section-title cta-final-title">Запишитесь на первую консультацию</h2><p class="section-text specialist-cta-card__text">Выберите удобное время и начните работу со специалистом уже сегодня.</p><a id="specialist-booking-cta-link" class="specialist-button specialist-button--primary specialist-button--large cta-final-button" href="#">Записаться на консультацию</a></div></div></section>
    </main>

    <main id="public-specialist-loading" class="wrap"><section><p>Загружаем профиль специалиста...</p></section></main>
    <main id="public-specialist-not-found" class="wrap specialist-hidden">
      <section>
        <h1>Профиль не найден</h1>
        <p>Проверьте ссылку или вернитесь на главную страницу.</p>
        <p><a class="button" href="/">На главную</a></p>
      </section>
    </main>
    <script>
      (function() {
        const slug = __PUBLIC_SLUG_JSON__;
        const apiBaseUrl = __PUBLIC_API_BASE_URL_JSON__;
        const specialistPageEl = document.getElementById('specialist-page');
        const loadingEl = document.getElementById('public-specialist-loading');
        const notFoundEl = document.getElementById('public-specialist-not-found');
        const nameEl = document.getElementById('public-specialist-display-name');
        const specializationEl = document.getElementById('public-specialist-specialization');
        const heroNameEl = document.getElementById('public-specialist-hero-name');
        const heroSpecializationEl = document.getElementById('public-specialist-hero-specialization');
        const quoteEl = document.getElementById('public-specialist-hero-quote');
        const heroPhotoImageEl = document.getElementById('public-specialist-hero-photo-image');
        const heroPhotoFallbackEl = document.getElementById('public-specialist-hero-photo-fallback');
        const bookingCtaLinkEl = document.getElementById('specialist-booking-cta-link');
        const headerBookLinkEl = document.getElementById('specialist-header-book-link');
        const contactLinkEl = document.getElementById('specialist-contact-link');
        const contactsEl = document.getElementById('specialist-contacts');
        const aboutEl = document.getElementById('specialist-about-content');
        const educationEl = document.getElementById('specialist-education-content');
        const documentsEl = document.getElementById('specialist-documents-content');
        const servicesEl = document.getElementById('specialist-services-content');
        const reviewsEl = document.getElementById('specialist-reviews-content');
        const sectionNavEl = document.getElementById('specialist-section-nav');
        const subnavListEl = sectionNavEl
          ? sectionNavEl.querySelector('.specialist-subnav__list')
          : null;
        const publicProfileApiUrl = `${apiBaseUrl.replace(/\\/$/, '')}/api/public/specialists/${encodeURIComponent(slug)}`;

        let runtimeState = 'loading';
        let bootstrapWatchdog = null;

        const cleanupBootstrapFailSafe = () => {
          if (bootstrapWatchdog !== null) {
            window.clearTimeout(bootstrapWatchdog);
            bootstrapWatchdog = null;
          }
          window.removeEventListener('error', showNotFound);
          window.removeEventListener('unhandledrejection', showNotFound);
        };

        const setRuntimeState = (state) => {
          runtimeState = state;

          if (!specialistPageEl || !loadingEl || !notFoundEl) {
            return;
          }

          specialistPageEl.classList.toggle('specialist-page--hidden', state !== 'success');
          specialistPageEl.setAttribute('aria-hidden', state === 'success' ? 'false' : 'true');

          loadingEl.classList.toggle('specialist-hidden', state !== 'loading');
          loadingEl.setAttribute('aria-hidden', state === 'loading' ? 'false' : 'true');

          notFoundEl.classList.toggle('specialist-hidden', state !== 'not-found');
          notFoundEl.setAttribute('aria-hidden', state === 'not-found' ? 'false' : 'true');

          window.dispatchEvent(new CustomEvent('public-specialist-state-change', { detail: { state: state } }));

          if (state !== 'loading') {
            cleanupBootstrapFailSafe();
          }
        };

        const showNotFound = () => {
          if (runtimeState !== 'loading') {
            return;
          }
          if (loadingEl) { loadingEl.style.display = 'none'; }
          if (notFoundEl) { notFoundEl.classList.remove('specialist-hidden'); }
          setRuntimeState('not-found');
        };

        if (!specialistPageEl || !loadingEl || !notFoundEl || !nameEl || !specializationEl || !heroNameEl || !heroSpecializationEl || !quoteEl || !heroPhotoImageEl || !heroPhotoFallbackEl) {
          showNotFound();
          return;
        }

        setRuntimeState('loading');

        window.addEventListener('error', showNotFound);
        window.addEventListener('unhandledrejection', showNotFound);

        const setSectionHtml = (el, value) => {
          if (!el) {
            return false;
          }
          const normalized = String(value || '').trim();
          if (!normalized) {
            const section = el.closest('section');
            if (section) {
              section.remove();
            }
            return false;
          }
          el.textContent = normalized;
          return true;
        };

        const renderSimpleList = (el, items, listClass, itemClass) => {
          if (!el) {
            return;
          }
          if (!Array.isArray(items) || items.length === 0) {
            const section = el.closest('section');
            if (section) {
              section.remove();
            }
            return;
          }
          const listEl = document.createElement('ul');
          listEl.className = listClass;
          items.forEach((item) => {
            const li = document.createElement('li');
            li.className = itemClass;
            li.textContent = String(item || '').trim();
            listEl.appendChild(li);
          });
          el.innerHTML = '';
          el.appendChild(listEl);
        };

        const renderServices = (blocks) => {
          if (!servicesEl) {
            return;
          }

          const servicesBlock = Array.isArray(blocks)
            ? blocks.find((block) => String((block && block.block_type) || '').trim().toLowerCase() === 'services')
            : null;

          let candidate = null;
          if (servicesBlock && servicesBlock.items != null) {
            candidate = servicesBlock.items;
          } else if (servicesBlock && servicesBlock.content != null) {
            candidate = servicesBlock.content;
          } else if (servicesBlock && servicesBlock.body != null) {
            candidate = servicesBlock.body;
          } else if (servicesBlock && servicesBlock.text != null) {
            candidate = servicesBlock.text;
          }

          const toServiceItem = (item) => {
            if (typeof item === 'string') {
              const title = String(item || '').trim();
              return title ? { name: title, price: '', description: '' } : null;
            }
            if (!item || typeof item !== 'object') {
              return null;
            }
            const name = String((item && item.name) || '').trim();
            const price = String((item && item.price) || '').trim();
            const description = String((item && (item.description || item.body || item.text)) || '').trim();
            if (!name && !price && !description) {
              return null;
            }
            return { name, price, description };
          };

          let services = [];
          if (Array.isArray(candidate)) {
            services = candidate.map(toServiceItem).filter((item) => item !== null);
          } else if (typeof candidate === 'string') {
            services = candidate
              .split(/\\r?\\n/)
              .map((line) => toServiceItem(line))
              .filter((item) => item !== null);
          }

          if (services.length === 0) {
            const section = servicesEl.closest('section');
            if (section) {
              section.remove();
            }
            return;
          }

          const listEl = document.createElement('ul');
          listEl.className = 'specialist-list';

          const buildServiceLabel = (item) => {
            const serviceName = String(item.name || '').trim();
            const serviceDescription = String(item.description || '').trim();

            if (serviceName && serviceDescription) {
              return `${serviceName} — ${serviceDescription}`;
            }

            return serviceName || serviceDescription;
          };

          services.forEach((item) => {
            const serviceLabel = buildServiceLabel(item);

            if (!serviceLabel) {
              return;
            }

            const servicePrice = String(item.price || '').trim();
            const row = document.createElement('li');
            row.className = 'specialist-list__item specialist-list__item--service';

            const title = document.createElement('span');
            title.textContent = serviceLabel;
            row.appendChild(title);

            if (servicePrice) {
              const price = document.createElement('span');
              price.className = 'specialist-service__price';
              price.textContent = servicePrice;
              row.appendChild(price);
            }

            listEl.appendChild(row);
          });

          if (!listEl.children.length) {
            const section = servicesEl.closest('section');
            if (section) {
              section.remove();
            }
            return;
          }

          servicesEl.innerHTML = '';
          servicesEl.appendChild(listEl);
        };

        const collectBlocks = (blocks) => {
          const acc = { about: '', education: '', services: '' };
          if (!Array.isArray(blocks)) {
            return acc;
          }

          blocks.forEach((block) => {
            const blockType = block && block.block_type ? block.block_type : '';
            const blockKind = block && block.kind ? block.kind : '';
            const kind = String(blockType || blockKind || '').trim().toLowerCase();
            const blockContent = block && block.content ? block.content : '';
            const value = String(blockContent || '').trim();
            if (!value) {
              return;
            }
            if (kind === 'about') {
              acc.about = value;
            } else if (kind === 'education') {
              acc.education = value;
            } else if (kind === 'services') {
              acc.services = value;
            }
          });

          return acc;
        };

        // Legacy signature reference: const renderReviews = (reviewsData, blocks) => {
        const renderReviews = (blocks) => {
          if (!reviewsEl) {
            return;
          }
          let candidate = null;

          const normalizeReview = (raw) => {
            if (typeof raw === 'string') {
              const text = String(raw || '').trim();
              return text ? { text, author: '' } : null;
            }
            if (!raw || typeof raw !== 'object') {
              return null;
            }
            const text = String((raw && (raw.text || raw.content || raw.body)) || '').trim();
            const author = String((raw && (raw.author || raw.name)) || '').trim();
            if (!text) {
              return null;
            }
            return { text, author };
          };

          const payload = blocks && typeof blocks === 'object' && !Array.isArray(blocks) ? blocks : null;
          const reviewsData = payload && Array.isArray(payload.reviews) ? payload.reviews : (Array.isArray(blocks) ? blocks : []);
          const blocksSource = payload && Array.isArray(payload.blocks) ? payload.blocks : (Array.isArray(blocks) ? blocks : null);

          let reviews = [];
          if (Array.isArray(reviewsData) && reviewsData.length > 0) {
            reviews = reviewsData.map((item) => normalizeReview(item)).filter((item) => item !== null);
          // Legacy branch reference: } else if (Array.isArray(blocks)) {
          } else if (Array.isArray(blocksSource)) {
            // Legacy branch reference: const reviewsBlock = blocks.find((block) => String((block && block.block_type) || '').trim().toLowerCase() === 'reviews');
            const reviewsBlock = blocksSource.find((block) => String((block && block.block_type) || '').trim().toLowerCase() === 'reviews');
            if (reviewsBlock && reviewsBlock.items != null) {
              candidate = reviewsBlock.items;
            } else if (reviewsBlock && reviewsBlock.content != null) {
              candidate = reviewsBlock.content;
            } else if (reviewsBlock && reviewsBlock.body != null) {
              candidate = reviewsBlock.body;
            } else if (reviewsBlock && reviewsBlock.text != null) {
              candidate = reviewsBlock.text;
            }

            if (Array.isArray(candidate)) {
              reviews = candidate.map((item) => normalizeReview(item)).filter((item) => item !== null);
            } else if (typeof candidate === 'string') {
              reviews = candidate.split(/\\r?\\n/).map((line) => normalizeReview(line)).filter((item) => item !== null);
            }
          }

          if (reviews.length === 0) {
            const section = reviewsEl.closest('section');
            if (section) {
              section.remove();
            }
            return;
          }

          const listEl = document.createElement('ul');
          listEl.className = 'reviews-grid';
          reviews.forEach((item) => {
            const card = document.createElement('li');
            card.className = 'review-card';

            const text = document.createElement('p');
            text.className = 'review-text';
            text.textContent = item.text;
            card.appendChild(text);

            if (item.author) {
              const author = document.createElement('p');
              author.className = 'review-author';
              author.textContent = item.author;
              card.appendChild(author);
            }

            listEl.appendChild(card);
          });
          reviewsEl.innerHTML = '';
          reviewsEl.appendChild(listEl);
        };

        const renderDocuments = (media) => {
          if (!documentsEl) {
            return;
          }

          documentsEl.innerHTML = '';
          const documentItems = Array.isArray(media)
            ? media
              .filter((item) => String((item && item.media_type) || '').trim().toLowerCase() === 'document')
              .map((item) => ({
                title: String((item && item.title) || '').trim(),
                url: typeof (item && item.url) === 'string' ? item.url.trim() : '',
              }))
              .filter((item) => item.title.length > 0)
            : [];

          if (documentItems.length === 0) {
            const documentsSectionEl = documentsEl.closest('section');
            if (documentsSectionEl) {
              documentsSectionEl.remove();
            }
            return;
          }

          const listEl = document.createElement('ul');
          listEl.className = 'specialist-grid specialist-grid--documents';
          let hasUnavailableDocumentUrl = false;

          documentItems.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'specialist-grid-card';
            if (/^https?:\\/\\//i.test(item.url)) {
              const link = document.createElement('a');
              link.href = item.url;
              link.textContent = item.title;
              link.target = '_blank';
              link.rel = 'noopener noreferrer';
              link.className = 'specialist-grid-card__title';
              li.appendChild(link);
            } else {
              const title = document.createElement('span');
              title.textContent = item.title;
              title.className = 'specialist-grid-card__title';
              li.appendChild(title);
              hasUnavailableDocumentUrl = true;
            }
            const meta = document.createElement('p');
            meta.className = 'specialist-grid-card__meta';
            meta.textContent = 'Документ специалиста';
            li.appendChild(meta);
            listEl.appendChild(li);
          });

          documentsEl.appendChild(listEl);

          if (hasUnavailableDocumentUrl) {
            const hint = document.createElement('p');
            hint.textContent = 'Скоро будет доступно скачивание';
            documentsEl.appendChild(hint);
          }
        };

        const updateStickyOffsets = () => {
          const headerHeight = document.getElementById('specialist-sticky-header')
            ? document.getElementById('specialist-sticky-header').getBoundingClientRect().height
            : 72;
          const navHeight = sectionNavEl ? sectionNavEl.getBoundingClientRect().height : 0;
          const totalOffset = Math.ceil(headerHeight + navHeight + 16);

          document.documentElement.style.setProperty('--specialist-header-height', `${Math.ceil(headerHeight)}px`);
          document.documentElement.style.setProperty('--specialist-subnav-height', `${Math.ceil(navHeight)}px`);
          document.documentElement.style.setProperty('--specialist-sticky-offset', `${totalOffset}px`);
        };

        const syncSubnavVisibility = () => {
          if (!sectionNavEl || !subnavListEl) {
            return [];
          }

          const links = Array.from(subnavListEl.querySelectorAll('[data-section-id]'));
          const visibleSectionIds = [];

          links.forEach((link) => {
            const sectionId = link.getAttribute('data-section-id');
            const sectionEl = sectionId ? document.getElementById(sectionId) : null;
            const isVisible = Boolean(sectionEl && sectionEl.parentElement);
            if (isVisible) {
              visibleSectionIds.push(sectionId);
              link.classList.remove('specialist-hidden');
            } else {
              link.classList.add('specialist-hidden');
            }
          });

          if (visibleSectionIds.length === 0) {
            sectionNavEl.classList.add('specialist-hidden');
          } else {
            sectionNavEl.classList.remove('specialist-hidden');
          }

          return visibleSectionIds;
        };

        const setupSubnavActiveTracking = (sectionIds) => {
          if (!subnavListEl || !Array.isArray(sectionIds) || sectionIds.length === 0) {
            return;
          }

          const navLinks = Array.from(subnavListEl.querySelectorAll('a[data-section-id]'));
          const trackedSections = sectionIds
            .map((id) => {
              const sectionEl = document.getElementById(id);
              if (!sectionEl || !sectionEl.parentElement) {
                return null;
              }
              return { id, sectionEl };
            })
            .filter((item) => Boolean(item));

          if (trackedSections.length === 0) {
            return;
          }

          let activeId = trackedSections[0].id;
          let ticking = false;
          let suppressAutoTrackingUntil = 0;

          const readStickyOffset = () => {
            updateStickyOffsets();
            const rawValue = window.getComputedStyle(document.documentElement).getPropertyValue('--specialist-sticky-offset') || '';
            const parsed = Number.parseFloat(rawValue);
            if (Number.isFinite(parsed)) {
              return parsed;
            }
            const headerEl = document.getElementById('specialist-sticky-header');
            const headerHeight = headerEl ? headerEl.getBoundingClientRect().height : 72;
            const navHeight = sectionNavEl ? sectionNavEl.getBoundingClientRect().height : 0;
            return Math.ceil(headerHeight + navHeight + 16);
          };

          const setActive = (id) => {
            if (!id || id === activeId) {
              return;
            }
            activeId = id;
            navLinks.forEach((link) => {
              const isActive = link.getAttribute('data-section-id') === id;
              link.classList.toggle('specialist-subnav__link--active', isActive);
              if (isActive) {
                link.setAttribute('aria-current', 'true');
                link.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'auto' });
              } else {
                link.removeAttribute('aria-current');
              }
            });
          };

          const applyInitialActive = () => {
            navLinks.forEach((link) => {
              const isActive = link.getAttribute('data-section-id') === activeId;
              link.classList.toggle('specialist-subnav__link--active', isActive);
              if (isActive) {
                link.setAttribute('aria-current', 'true');
              } else {
                link.removeAttribute('aria-current');
              }
            });
          };

          const resolveActiveSectionId = () => {
            const visibleTrackedSections = trackedSections.filter((item) => item.sectionEl && item.sectionEl.parentElement);
            if (visibleTrackedSections.length === 0) {
              return null;
            }

            const stickyOffset = readStickyOffset();
            const probeY = window.scrollY + stickyOffset + 12;
            let candidateId = visibleTrackedSections[0].id;

            visibleTrackedSections.forEach((item) => {
              const absoluteTop = item.sectionEl.getBoundingClientRect().top + window.scrollY;
              if (absoluteTop <= probeY) {
                candidateId = item.id;
              }
            });

            const nearBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
            if (nearBottom) {
              return visibleTrackedSections[visibleTrackedSections.length - 1].id;
            }

            return candidateId;
          };

          const updateActiveFromScroll = () => {
            if (Date.now() < suppressAutoTrackingUntil) {
              return;
            }
            const nextId = resolveActiveSectionId();
            if (nextId) {
              setActive(nextId);
            }
          };

          const scheduleUpdate = () => {
            if (ticking) {
              return;
            }
            ticking = true;
            window.requestAnimationFrame(() => {
              ticking = false;
              updateActiveFromScroll();
            });
          };

          applyInitialActive();
          scheduleUpdate();

          navLinks.forEach((link) => {
            link.addEventListener('click', (event) => {
              const targetId = link.getAttribute('data-section-id');
              const target = targetId ? document.getElementById(targetId) : null;
              if (!target) {
                return;
              }
              event.preventDefault();
              setActive(targetId);
              const stickyOffset = readStickyOffset();
              const absoluteTop = target.getBoundingClientRect().top + window.scrollY;
              const targetScrollTop = Math.max(0, absoluteTop - stickyOffset + 1);
              suppressAutoTrackingUntil = Date.now() + 450;
              window.scrollTo({ top: targetScrollTop, behavior: 'smooth' });
              window.history.replaceState(null, '', `#${targetId}`);
            });
          });

          window.addEventListener('scroll', scheduleUpdate, { passive: true });
          window.addEventListener('resize', scheduleUpdate);
        };

        const bootstrap = async () => {
          const response = await fetch(publicProfileApiUrl);
          if (!response.ok) {
            throw new Error(String(response.status));
          }
          const payload = await response.json();
          const profile = payload && payload.profile ? payload.profile : {};

            setRuntimeState('success');
            const displayName = String(profile.display_name || '').trim();
            const profileSpecialization = String(profile.specialization || '').trim();
            nameEl.textContent = displayName;
            specializationEl.textContent = profileSpecialization;
            heroNameEl.textContent = displayName;
            heroSpecializationEl.textContent = profileSpecialization;
            const heroQuote = String(profile.hero_quote || '').trim();
            quoteEl.textContent = heroQuote;
            if (heroQuote) {
              quoteEl.classList.remove('specialist-hidden');
            } else {
              quoteEl.classList.add('specialist-hidden');
            }

            const photoUrl = String(profile.photo_url || '').trim();
            if (photoUrl && /^https?:\\/\\//i.test(photoUrl)) {
              heroPhotoImageEl.src = photoUrl;
              heroPhotoImageEl.classList.remove('specialist-hidden');
              heroPhotoFallbackEl.classList.add('specialist-hidden');
            } else {
              heroPhotoImageEl.classList.add('specialist-hidden');
              heroPhotoFallbackEl.classList.remove('specialist-hidden');
            }

            const blocksSource = payload && payload.blocks ? payload.blocks : null;
            const blocks = collectBlocks(blocksSource);
            setSectionHtml(aboutEl, blocks.about);
            const educationItems = String(blocks.education || '').split(/\\r?\\n/).map((line) => line.trim()).filter((line) => line.length > 0);
            renderSimpleList(educationEl, educationItems, 'specialist-list specialist-list--education', 'specialist-list__item');
            // Legacy call reference: renderReviews(payload && Array.isArray(payload.reviews) ? payload.reviews : [], blocksSource);
            renderReviews(payload);
            renderDocuments(payload && payload.media ? payload.media : null);

            const clientBotUsername = String(profile.client_bot_username || '').trim();
            const specialistId = String(profile.id || '').trim();
            let bookingHref = '';
            if (clientBotUsername && specialistId) {
              bookingHref = `https://t.me/${encodeURIComponent(clientBotUsername)}?start=book_${encodeURIComponent(specialistId)}`;
              const contactHref = `https://t.me/${encodeURIComponent(clientBotUsername)}?start=contact_specialist_${encodeURIComponent(specialistId)}`;
              if (bookingCtaLinkEl) {
                bookingCtaLinkEl.href = bookingHref;
                bookingCtaLinkEl.target = '_blank';
                bookingCtaLinkEl.rel = 'noopener noreferrer';
              }
              if (contactLinkEl) {
                contactLinkEl.href = contactHref;
                contactLinkEl.target = '_blank';
                contactLinkEl.rel = 'noopener noreferrer';
              }
            }

            if (headerBookLinkEl) {
              if (bookingHref) {
                headerBookLinkEl.href = bookingHref;
                headerBookLinkEl.target = '_blank';
                headerBookLinkEl.rel = 'noopener noreferrer';
                headerBookLinkEl.classList.remove('specialist-hidden');
              } else {
                headerBookLinkEl.classList.add('specialist-hidden');
              }
            }

            renderServices(blocksSource);

            if (contactsEl) {
              const contacts = profile && profile.contacts ? profile.contacts : {};
              const contactRows = [
                { label: 'Telegram', value: String((contacts && contacts.telegram) || '').trim() },
                { label: 'WhatsApp', value: String((contacts && contacts.whatsapp) || '').trim() },
                { label: 'Телефон', value: String((contacts && contacts.phone) || '').trim() },
                { label: 'Email', value: String((contacts && contacts.email) || '').trim() },
              ].filter((item) => item.value.length > 0);

              if (contactRows.length === 0) {
                contactsEl.classList.add('specialist-hidden');
              } else {
                contactsEl.innerHTML = '';
                contactRows.forEach((item) => {
                  const li = document.createElement('li');
                  li.className = 'specialist-contacts__item';
                  const label = document.createElement('span');
                  label.className = 'specialist-contacts__label';
                  label.textContent = item.label;
                  const value = document.createElement('span');
                  value.className = 'specialist-contacts__value';
                  value.textContent = item.value;
                  li.appendChild(label);
                  li.appendChild(value);
                  contactsEl.appendChild(li);
                });
                contactsEl.classList.remove('specialist-hidden');
              }
            }

            const visibleSectionIds = syncSubnavVisibility();
            setupSubnavActiveTracking(visibleSectionIds);
            updateStickyOffsets();
            window.addEventListener('resize', updateStickyOffsets);

        };

        bootstrapWatchdog = window.setTimeout(() => {
          if (runtimeState === 'loading') {
            showNotFound();
          }
        }, 15000);

        try {
          bootstrap().catch(showNotFound);
        } catch (_error) {
          showNotFound();
        }
      })();
    </script>
  </body>
</html>
"""
    html = html.replace("__PUBLIC_SLUG_JSON__", json.dumps(public_slug))
    html = html.replace("__PUBLIC_API_BASE_URL_JSON__", json.dumps(config.BASE_URL))
    logger.info(
        "event=public_slug_route_rendered slug=%s route_name=%s api_base_url=%s",
        public_slug,
        route_name,
        config.BASE_URL,
    )
    return HTMLResponse(content=html)
