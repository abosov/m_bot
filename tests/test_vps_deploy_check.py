from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "vps_deploy_check.sh"


def test_check_script_is_checks_only() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "git pull" not in content
    assert "pip install" not in content
    assert "systemctl restart" not in content


def test_migrations_check_is_read_only() -> None:
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "read-only check" in content
    assert "psql" not in content
