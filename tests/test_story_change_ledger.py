from pathlib import Path
import os
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_HELPER = REPO_ROOT / "automation" / "scripts" / "story_change_ledger.sh"


def run_bash(cmd: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", cmd],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_append_story_change_ledger_entry_writes_normalized_jsonl(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    cmd = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry "
        "US-AUTO-23 review_outcome approve 2026-03-20_10-00-00 "
        "feature/us-auto-23 123 review_classification "
        "automation/runs/US-AUTO-23/2026-03-20_10-00-00/review_gate_result.json "
        "'review completed'"
    )
    result = run_bash(cmd, env)

    assert result.returncode == 0, result.stderr
    assert ledger_path.exists()
    line = ledger_path.read_text(encoding="utf-8").strip()
    assert '"story_id":"US-AUTO-23"' in line
    assert '"event":"review_outcome"' in line
    assert '"outcome":"approve"' in line
    assert '"run_id":"2026-03-20_10-00-00"' in line
    assert '"pr_number":"123"' in line
    assert '"decision_source":"review_classification"' in line


def test_append_story_change_ledger_entry_accepts_missing_optional_metadata(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    cmd = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry US-AUTO-23 story_started"
    )
    result = run_bash(cmd, env)

    assert result.returncode == 0, result.stderr
    line = ledger_path.read_text(encoding="utf-8").strip()
    assert '"event":"story_started"' in line
    assert '"run_id":null' in line
    assert '"branch":null' in line
    assert '"pr_number":null' in line


def test_append_story_change_ledger_entry_rejects_unknown_event(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    cmd = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry US-AUTO-23 unsupported_event"
    )
    result = run_bash(cmd, env)

    assert result.returncode != 0
    assert not ledger_path.exists()
