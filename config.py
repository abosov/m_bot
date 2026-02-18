import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

VALID_LOG_FORMATS = {"kv", "json"}

ENV_LOCAL_FILENAME = ".env.local"
ENV_LOCAL_PATH = Path(__file__).resolve().parent / ENV_LOCAL_FILENAME

_ENV_LOADED = False
APP_ENV = None
ENV_LOCAL_FOUND = False


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_app_env(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"production", "prod"}:
        return "prod"
    if normalized in {"development", "dev", "local"}:
        return "local"
    return normalized


def _determine_app_env() -> tuple[str, bool, bool]:
    explicit_env = os.getenv("APP_ENV")
    env_local_exists = ENV_LOCAL_PATH.is_file()
    if explicit_env:
        normalized_env = _normalize_app_env(explicit_env)
        if normalized_env != explicit_env:
            os.environ["APP_ENV"] = normalized_env
        return normalized_env, env_local_exists, False

    inferred_env = "local" if env_local_exists else "prod"
    os.environ["APP_ENV"] = inferred_env
    return inferred_env, env_local_exists, True


def is_test_env() -> bool:
    if (APP_ENV or "") == "test":
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    return "pytest" in sys.modules


def load_environment() -> None:
    global _ENV_LOADED, APP_ENV, ENV_LOCAL_FOUND
    if _ENV_LOADED:
        return

    app_env, env_local_exists, inferred = _determine_app_env()
    APP_ENV = app_env
    ENV_LOCAL_FOUND = env_local_exists

    if app_env == "local" and env_local_exists:
        load_dotenv(ENV_LOCAL_PATH, override=True)

    if inferred:
        logger.info(
            "APP_ENV not set. Auto-detected environment=%s (env_local_found=%s).",
            app_env,
            env_local_exists,
        )
    else:
        logger.info("APP_ENV explicitly set to %s.", app_env)

    logger.info("Env file %s found=%s.", ENV_LOCAL_FILENAME, env_local_exists)
    logger.info("ENABLE_READYZ=%s.", os.getenv("ENABLE_READYZ", "not set"))

    _ENV_LOADED = True


load_environment()


def _require_in_prod(name: str, value: str | None) -> str | None:
    return value


def _env_or_default(name: str, default: str, *, allow_empty_in_prod: bool = True) -> str:
    value = os.getenv(name)
    if value:
        return value
    if APP_ENV == "prod" and not is_test_env() and allow_empty_in_prod:
        return ""
    return default


def parse_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        value = default
    else:
        try:
            value = int(raw_value)
        except ValueError:
            raise ValueError(f"{name} must be an integer") from None

    if value < min_value or value > max_value:
        raise ValueError(f"{name} must be between {min_value} and {max_value}")

    return value

ENABLE_READYZ = _parse_bool(os.getenv("ENABLE_READYZ", str(APP_ENV == "prod")))
TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


def _resolve_encryption_key() -> str | None:
    key = os.getenv("ENCRYPTION_KEY")
    if key:
        return key

    if APP_ENV == "test" or os.getenv("PYTEST_RUNNING") == "1":
        os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY
        return TEST_ENCRYPTION_KEY

    return None

MASTER_BOT_TOKEN = _require_in_prod("MASTER_BOT_TOKEN", os.getenv("MASTER_BOT_TOKEN"))
ENCRYPTION_KEY = _require_in_prod("ENCRYPTION_KEY", _resolve_encryption_key())
GOOGLE_CLIENT_ID = _require_in_prod("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
GOOGLE_CLIENT_SECRET = _require_in_prod(
    "GOOGLE_CLIENT_SECRET",
    os.getenv("GOOGLE_CLIENT_SECRET"),
)
GOOGLE_REDIRECT_URI = _require_in_prod(
    "GOOGLE_REDIRECT_URI",
    _env_or_default("GOOGLE_REDIRECT_URI", "https://api.zumbot.ru/google/oauth/callback"),
)

BASE_URL = _require_in_prod("BASE_URL", _env_or_default("BASE_URL", "https://api.zumbot.ru"))
BACKEND_BASE_URL = BASE_URL
PUBLIC_SITE_URL = _require_in_prod(
    "PUBLIC_SITE_URL",
    _env_or_default("PUBLIC_SITE_URL", "https://zumbot.ru"),
)
WEB_CONNECT_PEPPER = _require_in_prod("WEB_CONNECT_PEPPER", os.getenv("WEB_CONNECT_PEPPER"))
WEB_CONNECT_COOKIE_NAME = _require_in_prod(
    "WEB_CONNECT_COOKIE_NAME",
    _env_or_default(
        "WEB_CONNECT_COOKIE_NAME",
        "zumbot_web_session",
        allow_empty_in_prod=False,
    ),
)
SUPPORT_TG_URL = _require_in_prod(
    "SUPPORT_TG_URL",
    _env_or_default(
        "SUPPORT_TG_URL",
        "https://t.me/zumbot_support",
        allow_empty_in_prod=False,
    ),
)

WEB_HOST = os.getenv("WEB_HOST")
if not WEB_HOST:
    WEB_HOST = "0.0.0.0" if APP_ENV == "local" else "127.0.0.1"

def _parse_int_env_or_default(name: str, default: int, min_value: int, max_value: int) -> int:
    try:
        return parse_int_env(name, default, min_value, max_value)
    except ValueError:
        return default


def _parse_int_env_runtime(name: str, default: int, min_value: int, max_value: int) -> int:
    try:
        return parse_int_env(name, default, min_value, max_value)
    except ValueError as exc:
        if APP_ENV == "prod" and not is_test_env():
            logger.error("Invalid %s=%r. Falling back to default %s.", name, os.getenv(name), default)
        else:
            logger.warning("Invalid %s=%r. Falling back to default %s (%s).", name, os.getenv(name), default, exc)
        return default


WEB_PORT = _parse_int_env_or_default("WEB_PORT", default=8000, min_value=1, max_value=65535)

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL and (APP_ENV != "prod" or is_test_env()):
    DATABASE_URL = "sqlite+aiosqlite:///./mvp.db"
DATABASE_URL = _require_in_prod("DB_URL", DATABASE_URL)

SERVICE_NAME = os.getenv("SERVICE_NAME", "backend")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
MAX_WEBHOOK_BODY_BYTES = _parse_int_env_or_default(
    "MAX_WEBHOOK_BODY_BYTES",
    default=1_000_000,
    min_value=1,
    max_value=10_000_000,
)
ALERTS_ENABLED = _parse_bool(os.getenv("ALERTS_ENABLED", "false"))
ALERTS_TELEGRAM_CHAT_ID = os.getenv("ALERTS_TELEGRAM_CHAT_ID")
ALERTS_TELEGRAM_TOKEN = os.getenv("ALERTS_TELEGRAM_TOKEN")
ALERTS_THROTTLE_SECONDS = _parse_int_env_or_default(
    "ALERTS_THROTTLE_SECONDS",
    default=60,
    min_value=0,
    max_value=86_400,
)
ALERTS_DEDUP_WINDOW_SECONDS = int(os.getenv("ALERTS_DEDUP_WINDOW_SECONDS", "300"))
APPOINTMENT_RESCHEDULE_MIN_NOTICE_HOURS = _parse_int_env_runtime(
    "APPOINTMENT_RESCHEDULE_MIN_NOTICE_HOURS",
    default=12,
    min_value=0,
    max_value=168,
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR") or None
LOG_FILE_PREFIX = os.getenv("LOG_FILE_PREFIX", "zumbot")
LOG_MAX_BYTES = _parse_int_env_runtime("LOG_MAX_BYTES", default=10_485_760, min_value=1_024, max_value=1_073_741_824)
LOG_BACKUP_COUNT = _parse_int_env_runtime("LOG_BACKUP_COUNT", default=5, min_value=1, max_value=100)
LOG_FORMAT = os.getenv("LOG_FORMAT", "kv").strip().lower() or "kv"


def _looks_like_database_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    if not parsed.scheme:
        return False

    # sqlite URL can be sqlite:///./mvp.db (no netloc)
    if parsed.scheme.startswith("sqlite"):
        return bool(parsed.path)

    return bool(parsed.netloc)


def validate_config() -> None:
    if APP_ENV != "prod" or is_test_env():
        return

    required_values = {
        "MASTER_BOT_TOKEN": MASTER_BOT_TOKEN,
        "ENCRYPTION_KEY": ENCRYPTION_KEY,
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
        "BASE_URL": BASE_URL,
        "PUBLIC_SITE_URL": PUBLIC_SITE_URL,
        "DB_URL": DATABASE_URL,
        "WEB_CONNECT_PEPPER": WEB_CONNECT_PEPPER,
    }

    errors: list[str] = []

    missing = [name for name, value in required_values.items() if not value]
    if missing:
        errors.append("Missing required variables: " + ", ".join(sorted(missing)))

    if DATABASE_URL and not _looks_like_database_url(DATABASE_URL):
        errors.append("Invalid value for DB_URL (must be a valid database URL)")

    int_specs = (
        ("WEB_PORT", 8000, 1, 65535),
        ("MAX_WEBHOOK_BODY_BYTES", 1_000_000, 1, 10_000_000),
        ("ALERTS_THROTTLE_SECONDS", 60, 0, 86_400),
        ("LOG_MAX_BYTES", 10_485_760, 1_024, 1_073_741_824),
        ("LOG_BACKUP_COUNT", 5, 1, 100),
    )
    for name, default, min_value, max_value in int_specs:
        try:
            parse_int_env(name, default, min_value, max_value)
        except ValueError as exc:
            errors.append(str(exc))

    valid_levels = set(logging._nameToLevel.keys())
    if LOG_LEVEL not in valid_levels:
        errors.append(f"LOG_LEVEL must be a valid logging level (got {LOG_LEVEL!r})")

    if LOG_FORMAT not in VALID_LOG_FORMATS:
        errors.append(
            f"LOG_FORMAT must be one of {sorted(VALID_LOG_FORMATS)} (got {LOG_FORMAT!r})"
        )

    if errors:
        raise RuntimeError(
            "Invalid production configuration:\n- " + "\n- ".join(errors)
        )

    logger.warning(
        "Production DB policy: run SQL migrations before startup; init_db(create_all) is retained only for backward compatibility."
    )
