import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vps_deploy_check.sh"


def _normalize(db_url: str) -> subprocess.CompletedProcess[str]:
    command = (
        "set -euo pipefail; "
        f"source '{SCRIPT_PATH}'; "
        f"normalize_db_url_to_pg_dsn '{db_url}'"
    )
    return subprocess.run(["bash", "-lc", command], capture_output=True, text=True)


@pytest.mark.parametrize(
    ("db_url", "expected"),
    [
        (
            "postgresql+asyncpg://user:pass@host:5432/dbname",
            "postgresql://user:pass@host:5432/dbname",
        ),
        (
            "postgres://user:pass@host:5432/dbname",
            "postgresql://user:pass@host:5432/dbname",
        ),
        (
            "postgresql://user:pass@host:5432/dbname?sslmode=require",
            "postgresql://user:pass@host:5432/dbname?sslmode=require",
        ),
    ],
)
def test_normalize_db_url_to_pg_dsn_success(db_url: str, expected: str) -> None:
    result = _normalize(db_url)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    "db_url",
    [
        "postgresql://user:pass@host:5432",
        "sqlite+aiosqlite:///tmp/test.db",
    ],
)
def test_normalize_db_url_to_pg_dsn_failure(db_url: str) -> None:
    result = _normalize(db_url)
    assert result.returncode != 0
