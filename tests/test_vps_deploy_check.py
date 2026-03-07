from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vps_deploy_check.sh"


def test_check_script_is_checks_only() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'MODE="checks"' in content
    assert 'if [[ "${MODE}" == "deploy" ]]; then' in content
    assert "run_checks" in content

    checks_block = content.split("run_checks()", 1)[1].split("run_deploy()", 1)[0]
    assert "git pull" not in checks_block
    assert "pip install" not in checks_block
    assert "systemctl restart" not in checks_block


def test_check_script_contains_build_and_dependency_checks() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "print_git_and_build_info" in content
    assert "PyYAML import failed" in content
    assert "check_migrations_applied" in content


def test_check_yaml_import_uses_venv_python3_and_simple_inline_import() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'local venv_python="${VENV_DIR}/bin/python3"' in content
    assert "\"${venv_python}\" -c \"import yaml; print('OK')\" >/dev/null" in content
    assert 'source "${VENV_DIR}/bin/activate"' not in content


def test_deploy_installs_zumbot_test_reset_symlink() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Install test reset command" in content
    assert "ln -sfn \"${REPO_DIR}/scripts/test_data_reset_run.py\" /usr/local/bin/zumbot-test-reset" in content


def test_deploy_contains_webhook_log_masking_smoke_check() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_webhook_secret_not_logged" in content
    assert "Smoke: webhook log masking" in content
    assert "TEST_PERSONAL_WEBHOOK_SECRET is required for webhook log masking smoke-check" in content
    assert "webhook masking marker not found in nginx access log" in content
    assert "raw webhook path detected in nginx access log" in content


def test_telegram_smoke_checks_are_ipv4_safe_and_reuse_helper() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'curl -4 -sS --connect-timeout 3 --max-time 8 "https://api.telegram.org/bot${token}/getMe"' in content
    assert 'run_step "Smoke: master bot getMe" check_telegram_getme "master bot" "${MASTER_BOT_TOKEN}"' in content
    assert 'run_step "Smoke: test personal bot getMe" check_telegram_getme "test personal bot" "${TEST_PERSONAL_BOT_TOKEN}"' in content
    assert 'urllib.request' not in content
