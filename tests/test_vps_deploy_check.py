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


def test_migrations_check_is_read_only() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "read-only check" in content
    assert "psql" not in content
