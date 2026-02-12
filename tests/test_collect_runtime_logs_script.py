from pathlib import Path
import subprocess


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collect_runtime_logs.sh"


def test_collect_runtime_logs_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_collect_runtime_logs_script_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
