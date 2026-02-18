import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_validate_config(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "import config; config.validate_config()"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _base_prod_env() -> dict[str, str]:
    return {
        "APP_ENV": "prod",
        "MASTER_BOT_TOKEN": "token",
        "ENCRYPTION_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "GOOGLE_CLIENT_ID": "cid",
        "GOOGLE_CLIENT_SECRET": "csecret",
        "GOOGLE_REDIRECT_URI": "https://example.test/callback",
        "BASE_URL": "https://example.test",
        "DB_URL": "sqlite+aiosqlite:///./mvp.db",
        "PUBLIC_SITE_URL": "https://example.test",
        "WEB_CONNECT_PEPPER": "pepper",
    }


def test_prod_missing_db_url_reports_db_url_name_only() -> None:
    env = _base_prod_env()
    env.pop("DB_URL")

    result = _run_validate_config(env)

    assert result.returncode != 0
    assert "Missing required variables" in result.stderr
    assert "DB_URL" in result.stderr


def test_prod_missing_multiple_required_vars_lists_all_names() -> None:
    env = _base_prod_env()
    env.pop("DB_URL")
    env.pop("MASTER_BOT_TOKEN")
    env.pop("GOOGLE_CLIENT_SECRET")

    result = _run_validate_config(env)

    assert result.returncode != 0
    assert "Missing required variables" in result.stderr
    for required_name in ("DB_URL", "MASTER_BOT_TOKEN", "GOOGLE_CLIENT_SECRET"):
        assert required_name in result.stderr


def test_max_webhook_body_bytes_zero_or_negative_fails() -> None:
    for invalid in ("0", "-1"):
        env = _base_prod_env()
        env["MAX_WEBHOOK_BODY_BYTES"] = invalid

        result = _run_validate_config(env)

        assert result.returncode != 0
        assert "MAX_WEBHOOK_BODY_BYTES must be between 1 and 10000000" in result.stderr


def test_web_port_zero_out_of_range_or_non_integer_fails() -> None:
    for invalid in ("0", "70000", "not-a-number"):
        env = _base_prod_env()
        env["WEB_PORT"] = invalid

        result = _run_validate_config(env)

        assert result.returncode != 0
        if invalid == "not-a-number":
            assert "WEB_PORT must be an integer" in result.stderr
        else:
            assert "WEB_PORT must be between 1 and 65535" in result.stderr


def test_alerts_throttle_seconds_negative_fails() -> None:
    env = _base_prod_env()
    env["ALERTS_THROTTLE_SECONDS"] = "-1"

    result = _run_validate_config(env)

    assert result.returncode != 0
    assert "ALERTS_THROTTLE_SECONDS must be between 0 and 86400" in result.stderr


def test_validate_config_passes_with_valid_values() -> None:
    env = _base_prod_env()
    env["WEB_PORT"] = "8001"
    env["MAX_WEBHOOK_BODY_BYTES"] = "2048"
    env["ALERTS_THROTTLE_SECONDS"] = "60"

    result = _run_validate_config(env)

    assert result.returncode == 0
    assert "Invalid production configuration" not in result.stderr
