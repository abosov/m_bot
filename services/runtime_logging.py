from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import config

SECRET_KEY_PATTERN = re.compile(
    r"(token|secret|password|passwd|authorization|api[_-]?key|webhook)",
    re.IGNORECASE,
)


class SafeLogFilter(logging.Filter):
    def __init__(self, max_len: int = 1024) -> None:
        super().__init__()
        self.max_len = max_len

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: _sanitize_value(key, value, self.max_len)
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(_sanitize_value(None, value, self.max_len) for value in record.args)

        message = record.getMessage()
        if len(message) > self.max_len:
            record.msg = f"{message[: self.max_len]}... [TRUNCATED]"
            record.args = ()

        return True


def _sanitize_value(key: str | None, value: object, max_len: int) -> str:
    key_name = (key or "").strip()
    if key_name and SECRET_KEY_PATTERN.search(key_name):
        return "[REDACTED]"

    as_text = str(value)
    if len(as_text) > max_len:
        return f"{as_text[:max_len]}... [TRUNCATED]"
    return as_text


class KVFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        message = record.getMessage().replace("\n", "\\n")
        logger_name = record.name
        return (
            f"ts={timestamp} level={record.levelname} logger={logger_name} "
            f"msg={json.dumps(message, ensure_ascii=False)}"
        )


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


def _build_formatter() -> logging.Formatter:
    if config.LOG_FORMAT == "json":
        return JSONFormatter()
    return KVFormatter()


def _build_rotating_file_handler(path: Path, formatter: logging.Formatter) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        filename=path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.addFilter(SafeLogFilter())
    return handler


def configure_runtime_logging() -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_zumbot_runtime_logging_configured", False):
        return

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    level_name = config.LOG_LEVEL.upper()
    level = logging.getLevelNamesMapping().get(level_name, logging.INFO)
    root_logger.setLevel(level)

    formatter = _build_formatter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(SafeLogFilter())
    root_logger.addHandler(stdout_handler)

    log_dir = config.LOG_DIR
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        prefix = config.LOG_FILE_PREFIX or "zumbot"

        app_handler = _build_rotating_file_handler(log_path / f"{prefix}.app.log", formatter)
        root_logger.addHandler(app_handler)

        http_logger = logging.getLogger("http")
        http_logger.handlers.clear()
        http_logger.setLevel(level)
        http_logger.propagate = True
        http_file_handler = _build_rotating_file_handler(log_path / f"{prefix}.http.log", formatter)
        http_logger.addHandler(http_file_handler)

        bot_logger = logging.getLogger("handlers")
        bot_logger.handlers.clear()
        bot_logger.setLevel(level)
        bot_logger.propagate = True
        bot_file_handler = _build_rotating_file_handler(log_path / f"{prefix}.bot.log", formatter)
        bot_logger.addHandler(bot_file_handler)

    root_logger._zumbot_runtime_logging_configured = True
