from __future__ import annotations

import logging
from typing import Any


def _normalize_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\n", " ")


def format_kv(*, event: str, **fields: Any) -> str:
    chunks = [f"event={event}"]
    for key, value in fields.items():
        chunks.append(f"{key}={_normalize_value(value)}")
    return " ".join(chunks)


def log_event(logger: logging.Logger, level: int, *, event: str, **fields: Any) -> None:
    logger.log(level, format_kv(event=event, **fields))
