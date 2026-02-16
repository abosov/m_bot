from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_encoding.py"


def test_check_encoding_ci_mode_passes() -> None:
    git_files = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    assert git_files.returncode == 0, git_files.stderr.decode("utf-8", errors="replace")

    paths = [p for p in git_files.stdout.decode("utf-8", errors="strict").split("\0") if p]
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--paths", *paths],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "scripts/check_encoding.py failed in CI mode (without --strict-warn).\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
