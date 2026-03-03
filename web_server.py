import json
import asyncio
import logging
import os
import re
import smtplib
import time
import uuid
from email.message import EmailMessage
from pathlib import Path
import requests
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import func, select, update
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    Appointment,
    BookingState,
    async_session_factory, 
    GoogleOAuth, 
    GoogleOAuthStatus, 
    OAuthState,
    OAuthStateType,
    SpecialistAuthTelegram,
    SpecialistProfile,
    CalendarSyncState,
    ServiceHeartbeat,
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
from services.request_context import get_request_id, reset_request_id, set_request_id
from services.alerting import close_alerting, notify_exception
from services import web_connect, web_session
import config
from admin_api import router as admin_router

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


def _request_id_from_request(request: Request) -> str:
    return getattr(request.state, "request_id", get_request_id())


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
app.add_middleware(RequestIdMiddleware)

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
        "/privacy-ru": "privacy-ru.html",
        "/terms-ru": "terms-ru.html",
        "/revoke-access-ru": "revoke-access-ru.html",
    }

    def _site_file(page: str) -> Path:
        return WEB_DIR / SITE_PAGES[page]

    @app.get("/")
    async def site_index() -> FileResponse:
        return FileResponse(_site_file("/"))

    @app.head("/")
    async def site_index_head() -> Response:
        return Response(status_code=200)

    @app.get("/features")
    async def site_features() -> FileResponse:
        return FileResponse(_site_file("/features"))

    @app.get("/pricing")
    async def site_pricing() -> FileResponse:
        return FileResponse(_site_file("/pricing"))

    @app.get("/specialists")
    async def site_specialists() -> FileResponse:
        return FileResponse(_site_file("/specialists"))

    @app.get("/contacts")
    async def site_contacts() -> FileResponse:
        return FileResponse(_site_file("/contacts"))

    @app.get("/privacy")
    async def site_privacy() -> FileResponse:
        return FileResponse(_site_file("/privacy"))

    @app.head("/privacy")
    async def site_privacy_head() -> Response:
        return Response(status_code=200)

    @app.get("/terms")
    async def site_terms() -> FileResponse:
        return FileResponse(_site_file("/terms"))

    @app.head("/terms")
    async def site_terms_head() -> Response:
        return Response(status_code=200)

    @app.get("/revoke-access")
    async def site_revoke_access() -> FileResponse:
        return FileResponse(_site_file("/revoke-access"))

    @app.head("/revoke-access")
    async def site_revoke_access_head() -> Response:
        return Response(status_code=200)

    @app.get("/privacy-ru")
    async def site_privacy_ru() -> FileResponse:
        return FileResponse(_site_file("/privacy-ru"))

    @app.head("/privacy-ru")
    async def site_privacy_ru_head() -> Response:
        return Response(status_code=200)

    @app.get("/terms-ru")
    async def site_terms_ru() -> FileResponse:
        return FileResponse(_site_file("/terms-ru"))

    @app.head("/terms-ru")
    async def site_terms_ru_head() -> Response:
        return Response(status_code=200)

    @app.get("/revoke-access-ru")
    async def site_revoke_access_ru() -> FileResponse:
        return FileResponse(_site_file("/revoke-access-ru"))

    @app.head("/revoke-access-ru")
    async def site_revoke_access_ru_head() -> Response:
        return Response(status_code=200)
else:
    logger.warning(
        "Static site disabled: expected index=%s assets_dir=%s",
        INDEX_FILE,
        ASSETS_DIR,
    )

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

logger.info("readyz endpoint enabled=%s", config.ENABLE_READYZ)
if config.ADMIN_API_KEY:
    app.include_router(admin_router)
    logger.info("admin API enabled at /admin/*")
else:
    logger.info("admin API disabled (ADMIN_API_KEY not set)")


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "backend", **get_build_info()}


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
    button { border: 0; border-radius: 10px; background: #2563eb; color: #fff; font-size: 16px; font-weight: 600; padding: 12px 20px; cursor: pointer; }
    button:disabled { background: #94a3b8; cursor: not-allowed; }
    .hint { color: #475569; font-size: 14px; }
    .warn { margin: 16px 0; border-radius: 8px; padding: 12px; background: #fff7ed; border: 1px solid #fdba74; }
  </style>
</head>
<body>
  <main>
    <h1>Подключение Google Календаря</h1>
    <p>Авторизация Google откроется в обычной странице браузера (не во встроенном скрытом iframe).</p>
    <div id="webview-warning" class="warn" hidden>Откройте в браузере (Safari/Chrome), иначе Google может блокировать вход.</div>
    <p class="hint">Продолжая, вы соглашаетесь с <a href="https://zumbot.ru/privacy-ru">Политикой конфиденциальности</a> и <a href="https://zumbot.ru/terms-ru">Условиями использования</a>.</p>
    <form action="/google/oauth/start" method="post">
      <button id="google-connect-btn" type="submit" disabled>Подключить Google</button>
    </form>
  </main>
  <script>
    (function () {
      const button = document.getElementById('google-connect-btn');
      const warning = document.getElementById('webview-warning');
      const ua = navigator.userAgent || '';
      if (ua.includes('Telegram') || ua.includes('WebView')) {
        warning.hidden = false;
      }

      const hash = window.location.hash || '';
      const params = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : hash);
      const token = params.get('token') || params.get('t');

      function enableButton() {
        button.disabled = false;
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
            enableButton();
            return;
          }
        }

        const sessionOk = await checkStatus();
        if (sessionOk) {
          enableButton();
        }
      }

      init();
    })();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/success")
async def success_page() -> HTMLResponse:
    text = "Google Календарь подключён. Вернитесь в Telegram, чтобы продолжить настройку."
    telegram_url = "https://t.me/zumhelper_bot"

    html = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Готово</title>
</head>
<body>
  <main>
    <h1>Готово</h1>
    <p>{text}</p>
    <p><a href="{telegram_url}">Открыть Telegram</a></p>
  </main>
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
