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
