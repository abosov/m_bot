import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aiogram import Bot

import config

logger = logging.getLogger(__name__)

_MAX_FIELD_LENGTH = 300
_MAX_MESSAGE_LENGTH = 3500

_SECRET_KEY_MARKERS = {
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "db_url",
}

_TOKEN_PATTERNS = [
    re.compile(r"\b\d{7,10}:[A-Za-z0-9_-]{20,}\b"),  # Telegram token
    re.compile(r"(?i)\b(refresh_token|access_token|client_secret)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"(?i)(postgres(?:ql)?://[^:\s]+:)[^@\s]+(@)"),
    re.compile(r"(?i)(mysql://[^:\s]+:)[^@\s]+(@)"),
]


@dataclass(slots=True)
class AlertEvent:
    title: str
    where: str
    error: str | None = None
    message: str | None = None
    stage: str | None = None
    user_message: str | None = None
    username: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


def sanitize_context(context: dict | None) -> dict[str, Any]:
    if not context:
        return {}

    def _sanitize_value(key: str, value: Any) -> Any:
        key_l = key.lower()
        if any(marker in key_l for marker in _SECRET_KEY_MARKERS):
            return "[REDACTED]"

        if isinstance(value, dict):
            return {str(k): _sanitize_value(str(k), v) for k, v in value.items()}
        if isinstance(value, list):
            return [_sanitize_value(key, item) for item in value]

        text = str(value)
        for pattern in _TOKEN_PATTERNS:
            text = pattern.sub(_replacement_for_pattern(pattern, text), text)

        if len(text) > _MAX_FIELD_LENGTH:
            text = f"{text[:_MAX_FIELD_LENGTH]}..."
        return text

    return {str(k): _sanitize_value(str(k), v) for k, v in context.items()}


def _replacement_for_pattern(pattern: re.Pattern[str], text: str):
    if pattern.pattern.startswith("(?i)(postgres") or pattern.pattern.startswith("(?i)(mysql"):
        return r"\1[REDACTED]\2"
    return "[REDACTED]"


_alert_lock = asyncio.Lock()
_dedup_cache: dict[str, float] = {}
_last_sent_ts = 0.0
_alert_bot: Bot | None = None
_alert_bot_token: str | None = None


async def close_alerting() -> None:
    global _alert_bot, _alert_bot_token

    bot = _alert_bot
    _alert_bot = None
    _alert_bot_token = None

    if bot is None:
        return

    try:
        await bot.session.close()
    except Exception:
        logger.warning("Failed to close alert bot session", exc_info=True)


def _normalize_message(message: str | None) -> str:
    if not message:
        return ""
    normalized = " ".join(message.split())
    if len(normalized) > 200:
        normalized = normalized[:200]
    return normalized


def _sanitize_text(value: str | None, max_length: int = _MAX_FIELD_LENGTH) -> str:
    if not value:
        return ""

    text = " ".join(value.split())
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub(_replacement_for_pattern(pattern, text), text)

    if len(text) > max_length:
        text = f"{text[:max_length]}..."
    return text


def _dedup_key(event: AlertEvent) -> str:
    context = sanitize_context(event.context)
    stable_parts = [
        event.where,
        event.stage or "",
        event.error or "",
        _normalize_message(event.message),
        str(context.get("specialist_id", "")),
        str(context.get("bot_id", "")),
    ]
    payload = "|".join(stable_parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _format_alert(event: AlertEvent) -> str:
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    safe_context = sanitize_context(event.context)

    lines = [
        f"ALERT: {event.title[:120]}",
        "",
        f"env={config.APP_ENV}",
    ]

    if event.stage:
        lines.append(f"stage={event.stage[:80]}")

    lines.append(
        f"where={event.where[:150]}",
    )

    if event.error:
        lines.append(f"error={event.error[:120]}")
    if event.message:
        lines.append(f"message={_normalize_message(event.message)}")
    if event.username:
        safe_username = event.username.lstrip("@")[:64]
        lines.append(f"username=@{safe_username}")
    if event.user_message:
        safe_user_message = _sanitize_text(event.user_message, max_length=_MAX_FIELD_LENGTH)
        if safe_user_message:
            lines.append(f'user_message="{safe_user_message}"')

    for key, value in safe_context.items():
        lines.append(f"{key}={value}")

    lines.append(f"time={ts}")
    rendered = "\n".join(lines)
    if len(rendered) > _MAX_MESSAGE_LENGTH:
        return f"{rendered[:_MAX_MESSAGE_LENGTH]}..."
    return rendered


def _alerts_enabled() -> bool:
    return bool(config.ALERTS_ENABLED)


def _resolve_alert_token() -> str | None:
    return config.ALERTS_TELEGRAM_TOKEN or config.MASTER_BOT_TOKEN


async def _get_alert_bot() -> Bot | None:
    global _alert_bot, _alert_bot_token

    token = _resolve_alert_token()
    if not token:
        logger.warning("Alerting skipped: no token configured")
        return None

    if _alert_bot is not None and _alert_bot_token == token:
        return _alert_bot

    previous_bot = _alert_bot
    _alert_bot = None
    _alert_bot_token = None

    if previous_bot is not None:
        try:
            await previous_bot.session.close()
        except Exception:
            logger.warning("Failed to close previous alert bot session", exc_info=True)

    try:
        new_bot = Bot(token=token)
    except Exception:
        _alert_bot = None
        _alert_bot_token = None
        raise
    else:
        _alert_bot = new_bot
        _alert_bot_token = token
        return _alert_bot


async def notify_admin(event: AlertEvent) -> None:
    global _last_sent_ts

    if not _alerts_enabled():
        return

    chat_id = config.ALERTS_TELEGRAM_CHAT_ID
    if not chat_id:
        logger.warning("Alerting enabled but ALERTS_TELEGRAM_CHAT_ID is not configured")
        return

    now = time.monotonic()
    dedup_key = _dedup_key(event)

    async with _alert_lock:
        dedup_window = max(1, int(config.ALERTS_DEDUP_WINDOW_SECONDS))
        throttle_seconds = max(0, int(config.ALERTS_THROTTLE_SECONDS))

        last_for_key = _dedup_cache.get(dedup_key)
        if last_for_key and now - last_for_key < dedup_window:
            return

        if throttle_seconds and now - _last_sent_ts < throttle_seconds:
            return

        bot = await _get_alert_bot()
        if bot is None:
            return

        message = _format_alert(event)
        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception:
            logger.warning("Failed to deliver admin alert", exc_info=True)
            return

        _dedup_cache[dedup_key] = now
        _last_sent_ts = now

        stale_before = now - dedup_window
        for key, sent_at in list(_dedup_cache.items()):
            if sent_at < stale_before:
                _dedup_cache.pop(key, None)


async def notify_exception(
    where: str,
    exc: Exception,
    context: dict | None = None,
    stage: str | None = None,
    user_message: str | None = None,
    username: str | None = None,
) -> None:
    await notify_admin(
        AlertEvent(
            title="Unhandled exception",
            where=where,
            error=exc.__class__.__name__,
            message=str(exc),
            context=sanitize_context(context),
            stage=stage,
            user_message=user_message,
            username=username,
        )
    )
