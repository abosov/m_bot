import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    if APP_ENV == "prod" and not is_test_env():
        return ""
    return default

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

WEB_HOST = os.getenv("WEB_HOST")
if not WEB_HOST:
    WEB_HOST = "0.0.0.0" if APP_ENV == "local" else "127.0.0.1"

WEB_PORT = int(os.getenv("WEB_PORT", "8000"))

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL and (APP_ENV != "prod" or is_test_env()):
    DATABASE_URL = "sqlite+aiosqlite:///./mvp.db"
DATABASE_URL = _require_in_prod("DB_URL", DATABASE_URL)

SERVICE_NAME = os.getenv("SERVICE_NAME", "backend")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
MAX_WEBHOOK_BODY_BYTES = int(os.getenv("MAX_WEBHOOK_BODY_BYTES", "1000000"))


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
    }

    missing = [name for name, value in required_values.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required production environment variables: " + ", ".join(missing)
        )

    logger.warning(
        "Production DB policy: run SQL migrations before startup; init_db(create_all) is retained only for backward compatibility."
    )
