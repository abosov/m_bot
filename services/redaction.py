from __future__ import annotations

import re

TELEGRAM_BOT_TOKEN_RE = re.compile(r"\b\d{7,14}:[A-Za-z0-9_-]{20,}\b")
BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
TOKEN_KV_RE = re.compile(
    r"(?i)(\b(?:access_token|refresh_token)\b\s*[:=]\s*[\"']?)([^\s&,\"'}]+)"
)
OAUTH_CODE_RE = re.compile(r"(?i)(\bcode=)([^&\s]+)")


def redact_text(text: str) -> str:
    redacted = TELEGRAM_BOT_TOKEN_RE.sub("[REDACTED_TELEGRAM_BOT_TOKEN]", text)
    redacted = BEARER_TOKEN_RE.sub("Bearer [REDACTED_BEARER_TOKEN]", redacted)
    redacted = TOKEN_KV_RE.sub(r"\1[REDACTED_TOKEN]", redacted)
    redacted = OAUTH_CODE_RE.sub(r"\1[REDACTED_OAUTH_CODE]", redacted)
    return redacted


def redact_exception(text: str) -> str:
    return redact_text(text)
