import importlib
import os
import subprocess
import sys
from pathlib import Path


def _clear_core_env(monkeypatch):
    for key in [
        "MASTER_BOT_TOKEN",
        "ENCRYPTION_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REDIRECT_URI",
        "BASE_URL",
        "PUBLIC_SITE_URL",
        "DB_URL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_config_import_does_not_fail_without_prod_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    _clear_core_env(monkeypatch)

    import config

    importlib.reload(config)


def test_validate_config_fails_in_real_prod_process_without_secrets():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import config; config.validate_config()",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env={"APP_ENV": "prod"},
        check=False,
    )

    assert result.returncode != 0
    assert "Missing required production environment variables" in result.stderr


def test_validate_config_skipped_for_test_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    _clear_core_env(monkeypatch)

    import config

    importlib.reload(config)
    config.validate_config()


def test_crypto_import_in_test_without_encryption_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    import config
    import services.crypto as crypto

    importlib.reload(config)
    importlib.reload(crypto)


def test_crypto_uses_fallback_key_in_test_when_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    import config
    import services.crypto as crypto

    importlib.reload(config)
    importlib.reload(crypto)

    encrypted = crypto.encrypt_token("hello")
    assert isinstance(encrypted, str)
    assert config.ENCRYPTION_KEY == config.TEST_ENCRYPTION_KEY


def test_test_key_used_when_pytest_running_flag_set(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    import config

    importlib.reload(config)

    assert config.ENCRYPTION_KEY == config.TEST_ENCRYPTION_KEY


def test_crypto_raises_in_prod_without_key_in_real_process():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import services.crypto as c; c.encrypt_token('hello')",
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env={"APP_ENV": "prod"},
        check=False,
    )

    assert result.returncode != 0
    assert "ENCRYPTION_KEY is required" in (result.stderr + result.stdout)


def test_export_logs_help_works_from_any_cwd():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "export_logs.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        env={**os.environ, "APP_ENV": "test", "PYTHONPATH": ""},
        check=False,
    )

    assert result.returncode == 0
    assert "Export Zumbot logs" in result.stdout


def test_export_logs_help_as_module_works_from_any_cwd():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.export_logs", "--help"],
        cwd="/tmp",
        capture_output=True,
        text=True,
        env={**os.environ, "APP_ENV": "test", "PYTHONPATH": str(repo_root)},
        check=False,
    )

    assert result.returncode == 0
    assert "Export Zumbot logs" in result.stdout


def test_export_logs_prints_venv_hint_when_repo_venv_exists(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = repo_root / ".venv"
    created = False
    if not venv_dir.exists():
        venv_dir.mkdir(parents=True)
        created = True

    try:
        script_path = repo_root / "scripts" / "export_logs.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            cwd="/tmp",
            capture_output=True,
            text=True,
            env={"APP_ENV": "test", "PYTHONPATH": ""},
            check=False,
        )
        assert result.returncode == 0
        assert "virtualenv is not activated" in result.stderr
    finally:
        if created:
            venv_dir.rmdir()
