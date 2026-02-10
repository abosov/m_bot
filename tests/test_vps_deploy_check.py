import os
import shlex
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vps_deploy_check.sh"


def _run_shell(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-lc", command], capture_output=True, text=True)


def _validate_url(db_url: str) -> subprocess.CompletedProcess[str]:
    command = (
        "set -euo pipefail; "
        f"source '{SCRIPT_PATH}'; "
        f"validate_psql_url '{db_url}'; "
        "echo 'OK'"
    )
    return _run_shell(command)


def _build_and_validate_url(db_url: str) -> subprocess.CompletedProcess[str]:
    command = (
        "set -euo pipefail; "
        f"source '{SCRIPT_PATH}'; "
        f"PSQL_URL=$(build_psql_url '{db_url}'); "
        "validate_psql_url \"${PSQL_URL}\"; "
        "echo \"${PSQL_URL}\""
    )
    return _run_shell(command)


@pytest.mark.parametrize(
    "db_url",
    [
        "postgresql://user:pass@host:5432/dbname",
        "postgres://user:pass@host:5432/dbname",
    ],
)
def test_validate_psql_url_success(db_url: str) -> None:
    result = _validate_url(db_url)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "OK"


@pytest.mark.parametrize(
    "db_url",
    [
        "postgresql://user:pass@host:5432",
        "sqlite+aiosqlite:///tmp/test.db",
    ],
)
def test_validate_psql_url_failure(db_url: str) -> None:
    result = _validate_url(db_url)
    assert result.returncode != 0


def test_run_sql_migrations_fails_on_psql_error(tmp_path: Path) -> None:
    env_file = tmp_path / "backend.env"
    env_file.write_text("DB_URL=postgresql+asyncpg://user:pass@host:5432/dbname\n", encoding="utf-8")

    migrations_dir = tmp_path / "scripts" / "migrations"
    migrations_dir.mkdir(parents=True)
    (migrations_dir / "001_fail.sql").write_text("select broken;\n", encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    psql_calls = tmp_path / "psql_calls.log"
    (fake_bin / "psql").write_text(
        "#!/usr/bin/env bash\n"
        "echo \"$*\" >> \"$PSQL_CALLS\"\n"
        "if [[ \"$*\" == *\"SELECT 1\"* ]]; then exit 0; fi\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "psql").chmod(0o755)

    command = (
        "set -euo pipefail; "
        f"source {shlex.quote(str(SCRIPT_PATH))}; "
        "sudo(){ if [[ \"$1\" == \"-u\" ]]; then shift 2; fi; \"$@\"; }; "
        f"REPO_DIR={shlex.quote(str(tmp_path))}; "
        f"ENV_FILE={shlex.quote(str(env_file))}; "
        "run_sql_migrations"
    )
    result = subprocess.run(
        ["bash", "-lc", command],
        capture_output=True,
        text=True,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}", "PSQL_CALLS": str(psql_calls)},
        check=False,
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "[FAIL] Run SQL migrations" in output
    assert "[OK] Run SQL migrations" not in output
    assert "postgresql://user:pass@host:5432/dbname" in psql_calls.read_text(encoding="utf-8")


def test_build_and_validate_psql_url_from_asyncpg() -> None:
    result = _build_and_validate_url("postgresql+asyncpg://user:pass@host:5432/dbname")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "postgresql://user:pass@host:5432/dbname"


def test_build_and_validate_psql_url_rejects_missing_dbname() -> None:
    result = _build_and_validate_url("postgresql+asyncpg://user:pass@host:5432")
    assert result.returncode != 0


def test_mask_url_hides_password() -> None:
    command = (
        "set -euo pipefail; "
        f"source '{SCRIPT_PATH}'; "
        "mask_url 'postgresql://user:secret-pass@host:5432/dbname'"
    )
    result = _run_shell(command)
    assert result.returncode == 0
    assert result.stdout.strip() == "postgresql://user:***@host:5432/dbname"


def test_run_sql_migrations_masks_url_in_verbose_logs(tmp_path: Path) -> None:
    env_file = tmp_path / "backend.env"
    env_file.write_text("DB_URL=postgresql+asyncpg://user:secret-pass@host:5432/dbname\n", encoding="utf-8")

    migrations_dir = tmp_path / "scripts" / "migrations"
    migrations_dir.mkdir(parents=True)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "psql").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$*\" == *\"SELECT 1\"* ]]; then exit 0; fi\n"
        "if [[ \"$*\" == *\"CREATE TABLE IF NOT EXISTS\"* ]]; then exit 0; fi\n"
        "if [[ \"$*\" == *\"SELECT 1 FROM applied_migrations\"* ]]; then exit 1; fi\n"
        "if [[ \"$*\" == *\"INSERT INTO applied_migrations\"* ]]; then exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "psql").chmod(0o755)

    command = (
        "set -euo pipefail; "
        f"source {shlex.quote(str(SCRIPT_PATH))}; "
        "sudo(){ if [[ \"$1\" == \"-u\" ]]; then shift 2; fi; \"$@\"; }; "
        f"REPO_DIR={shlex.quote(str(tmp_path))}; "
        f"ENV_FILE={shlex.quote(str(env_file))}; "
        "VERBOSE=1; "
        "run_sql_migrations"
    )

    result = subprocess.run(
        ["bash", "-lc", command],
        capture_output=True,
        text=True,
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
        check=False,
    )

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "secret-pass" not in output
    assert "postgresql://user:***@host:5432/dbname" in output
