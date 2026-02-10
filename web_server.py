import uuid
import json
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, update
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import (
    async_session_factory, 
    GoogleOAuth, 
    GoogleOAuthStatus, 
    SpecialistAuthTelegram,
    SpecialistProfile,
    ServiceHeartbeat,
    TelegramBot,
    TelegramBotStatus,
)
from services.google_oauth import exchange_code_for_token
from services.google_calendar import (
    GoogleCalendarInsufficientPermissionsError,
    list_calendars,
    scopes_as_string,
)
from services.crypto import encrypt_token
from logging_middleware import log_outbound_message
from services import heartbeat
from services.telegram.bot_factory import close_personal_bot_cache
from services.telegram.personal_dispatcher import process_update
import config
from admin_api import router as admin_router

logger = logging.getLogger(__name__)


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


app = FastAPI(lifespan=lifespan)

READYZ_DB_TIMEOUT_SEC = 2.0
READYZ_LOOP_TIMEOUT_SEC = 12.0
HEARTBEAT_WRITE_INTERVAL_SEC = 60.0
SERVICE_NAME = config.SERVICE_NAME
LAST_HEARTBEAT_WRITE_TS = 0.0
HEARTBEAT_WRITE_LOCK = asyncio.Lock()

MAX_WEBHOOK_BODY_BYTES = config.MAX_WEBHOOK_BODY_BYTES

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
    return {"status": "ok", "service": "backend"}


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
    logger.info(
        "readyz check result db_ok=%s loop_ok=%s latency_ms=%s",
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
            logger.info(
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
    content_length_header = request.headers.get("content-length")
    request_body: bytes | None = None

    if content_length_header:
        try:
            content_length = int(content_length_header)
            if content_length > MAX_WEBHOOK_BODY_BYTES:
                logger.warning(
                    "Webhook payload too large by content-length bot_id=%s size=%s limit=%s",
                    bot_id,
                    content_length,
                    MAX_WEBHOOK_BODY_BYTES,
                )
                return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
        except ValueError:
            request_body = await _read_request_body_with_limit(request, MAX_WEBHOOK_BODY_BYTES)
            if request_body is None:
                logger.warning(
                    "Webhook payload too large after body read bot_id=%s limit=%s",
                    bot_id,
                    MAX_WEBHOOK_BODY_BYTES,
                )
                return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
    else:
        request_body = await _read_request_body_with_limit(request, MAX_WEBHOOK_BODY_BYTES)
        if request_body is None:
            logger.warning(
                "Webhook payload too large after body read bot_id=%s limit=%s",
                bot_id,
                MAX_WEBHOOK_BODY_BYTES,
            )
            return JSONResponse(status_code=413, content={"detail": "payload_too_large"})

    try:
        if request_body is None:
            raw_update = await request.json()
        else:
            raw_update = json.loads(request_body)
    except Exception:
        logger.warning("Webhook payload is not valid JSON bot_id=%s", bot_id)
        return Response(status_code=200)

    async with async_session_factory() as session:
        stmt = select(TelegramBot).where(
            TelegramBot.bot_user_id == bot_id,
            TelegramBot.webhook_secret == secret,
            TelegramBot.status == TelegramBotStatus.active,
        )
        tg_bot = (await session.execute(stmt)).scalar_one_or_none()

    if tg_bot is None:
        logger.warning("Webhook auth failed for bot_id=%s", bot_id)
        return JSONResponse(status_code=404, content={"detail": "not_found"})

    update_id = raw_update.get("update_id")
    update_type = next((key for key in raw_update.keys() if key != "update_id"), "unknown")
    logger.info(
        "Webhook update accepted bot_id=%s specialist_id=%s update_id=%s update_type=%s",
        bot_id,
        tg_bot.specialist_id,
        update_id,
        update_type,
    )

    try:
        await process_update(tg_bot, raw_update)
    except Exception:
        logger.exception(
            "Webhook processing failed bot_id=%s specialist_id=%s update_id=%s",
            bot_id,
            tg_bot.specialist_id,
            update_id,
        )

    return Response(status_code=200)

@app.get("/google/oauth/callback", response_class=HTMLResponse)
async def google_oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return f"<h1>Ошибка авторизации: {error}</h1>"

    if not code or not state:
        return "<h1>Ошибка: Отсутствуют обязательные параметры (code, state)</h1>"

    try:
        specialist_id = uuid.UUID(state)
    except ValueError:
        return "<h1>Ошибка: Неверный формат state (ожидался UUID)</h1>"

    try:
        refresh_token, access_token, _ = exchange_code_for_token(code)

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

            await session.commit()

            permissions_ok = True
            try:
                await list_calendars(specialist_id)
            except GoogleCalendarInsufficientPermissionsError:
                permissions_ok = False
                logger.warning("Google connected but insufficient permissions specialist_id=%s", specialist_id)

            if auth_data and bot is not None:
                if permissions_ok:
                    text_out = "✅ **Google подключен!**\n\nШаг 4 из 4: выберите действие с календарем в master bot (создать отдельный или выбрать существующий)."
                else:
                    text_out = (
                        "⚠️ Google подключен, но доступов недостаточно для создания календаря/событий.\n"
                        "Переподключите аккаунт через кнопку в master bot и выдайте все права."
                    )
                try:
                    await bot.send_message(chat_id=auth_data.tg_user_id, text=text_out)
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

        return """
        <html>
            <head><title>Success</title></head>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1 style="color: green;">Успешно!</h1>
                <p>Google Календарь подключен.</p>
                <p>Вы можете закрыть это окно и вернуться в Telegram.</p>
                <script>setTimeout(function(){window.close()}, 3000);</script>
            </body>
        </html>
        """

    except Exception:
        logger.exception("google_oauth_callback failed specialist_state=%s", state)
        return "<h1>Произошла ошибка при подключении Google. Попробуйте ещё раз из Telegram.</h1>"
