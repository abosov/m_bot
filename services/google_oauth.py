import logging
import secrets
import asyncio
import time
import warnings
from datetime import datetime, timedelta, timezone
from typing import Tuple, Any
import uuid

from google_auth_oauthlib.flow import Flow
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import GoogleOAuth, GoogleOAuthStatus, OAuthState, OAuthStateType, async_session_factory
from services.alerting import notify_exception
from services.log_context import log_event
from services.google_calendar import required_scopes as calendar_required_scopes

# Конфигурация клиента Google из переменных окружения
# В продакшене лучше использовать файл client_secrets.json, но для MVP соберем словарь вручную
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [config.GOOGLE_REDIRECT_URI],
    }
}

SCOPES = calendar_required_scopes()
REDIRECT_URI = config.GOOGLE_REDIRECT_URI

logger = logging.getLogger(__name__)



class GoogleCalendarPrecheckError(Exception):
    code = "calendar_precheck_error"


class GoogleCalendarNotConnectedError(GoogleCalendarPrecheckError):
    code = "calendar_not_connected"


class GoogleCalendarReconnectRequiredError(GoogleCalendarPrecheckError):
    code = "calendar_reconnect_required"


def required_scopes() -> set[str]:
    return set(calendar_required_scopes())


def _parse_scopes(raw_scopes: str | None) -> set[str]:
    if not raw_scopes:
        return set()
    normalized = raw_scopes.replace(",", " ")
    return {item.strip() for item in normalized.split() if item.strip()}


async def get_granted_scopes(specialist_id: uuid.UUID) -> set[str]:
    async with async_session_factory() as session:
        oauth_entry = await session.get(GoogleOAuth, specialist_id)
    if oauth_entry is None:
        return set()
    return _parse_scopes(getattr(oauth_entry, "scopes", None))


async def assert_calendar_ready_for_booking(specialist_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        oauth_entry = await session.get(GoogleOAuth, specialist_id)

    if oauth_entry is None or getattr(oauth_entry, "status", None) != GoogleOAuthStatus.connected:
        raise GoogleCalendarNotConnectedError("calendar_not_connected")

    granted_scopes = _parse_scopes(getattr(oauth_entry, "scopes", None))
    missing_scopes = required_scopes() - granted_scopes
    if missing_scopes:
        raise GoogleCalendarReconnectRequiredError(
            "calendar_reconnect_required: missing scopes " + ",".join(sorted(missing_scopes))
        )


def _ensure_google_oauth_config() -> None:
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        if config.APP_ENV == "prod":
            raise RuntimeError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required in production."
            )

async def create_oauth_state(
    session: AsyncSession,
    specialist_id: uuid.UUID,
    state_type: OAuthStateType,
    ttl_seconds: int = 600,
) -> str:
    state = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    session.add(
        OAuthState(
            state=state,
            specialist_id=specialist_id,
            type=state_type,
            expires_at=expires_at,
        )
    )
    await session.flush()
    return state


def get_auth_url(state: str) -> str:
    """
    Генерирует ссылку для авторизации в Google.
    Использует заранее созданный state.
    """
    _ensure_google_oauth_config()
    flow = Flow.from_client_config(
        GOOGLE_CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    # access_type='offline' обязателен для получения refresh_token
    # prompt нужен для гарантированного получения refresh_token при переподключении
    # include_granted_scopes=False не подтягивает ранее выданные scope из других флоу
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='false',
        prompt='consent',
        state=state
    )
    
    return authorization_url

def exchange_code_for_token(code: str) -> Tuple[str, str, Any]:
    """
    Обменивает временный код на токены.
    Возвращает (refresh_token, access_token, credentials_object)
    """
    _ensure_google_oauth_config()

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r".*Scope has changed.*", category=Warning)
        warnings.filterwarnings(
            "ignore",
            message=r".*Scope has changed.*",
            category=Warning,
            module=r"google_auth_oauthlib\..*",
        )
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(code=code)

    creds = flow.credentials
    logger.info(
        "event=google_oauth_scopes_granted scopes=%s",
        getattr(creds, "scopes", None),
    )

    return creds.refresh_token, creds.token, creds


async def exchange_code_for_token_async(code: str, timeout: int = 15) -> Tuple[str, str, Any]:
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(exchange_code_for_token, code),
            timeout=timeout,
        )
        log_event(
            logger,
            logging.INFO,
            event="google_api_call",
            alias="exchange_code_for_token",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="ok",
        )
        return result
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            event="google_api_call",
            alias="exchange_code_for_token",
            duration_ms=int((time.monotonic() - started) * 1000),
            outcome="error",
            exception_class=exc.__class__.__name__,
        )
        logger.error("Google OAuth token exchange failed exception_class=%s", exc.__class__.__name__)
        await notify_exception(
            where="services.google_oauth.exchange_code_for_token_async",
            exc=exc,
        )
        raise
