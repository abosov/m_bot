from pathlib import Path
import os
import subprocess
import json


REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_HELPER = REPO_ROOT / "automation" / "scripts" / "story_change_ledger.sh"
RUN_STORY_SCRIPT = REPO_ROOT / "automation" / "scripts" / "run_story.sh"


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


def test_append_story_change_ledger_entry_appends_without_rewriting_existing_lines(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    first = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry US-AUTO-23 story_started started"
    )
    second = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry US-AUTO-23 review_outcome approve"
    )

    first_result = run_bash(first, env)
    second_result = run_bash(second, env)

    assert first_result.returncode == 0, first_result.stderr
    assert second_result.returncode == 0, second_result.stderr
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"event":"story_started"' in lines[0]
    assert '"event":"review_outcome"' in lines[1]


def test_run_story_appends_story_started_entry_before_runner_exec(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    bundle_dir = root_dir / "automation" / "bundles" / "active" / "US-AUTO-23"
    bundle_dir.mkdir(parents=True)

    for file_name in [
        "00_story.md",
        "01_context_bundle.md",
        "02_file_scope.md",
        "03_master_prompt.md",
        "04_review_checklist.md",
        "05_followups.md",
        "06_manual_actions.md",
    ]:
        (bundle_dir / file_name).write_text(f"# {file_name}\n", encoding="utf-8")

    validator = tmp_path / "validate_story_bundle.sh"
    validator.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    validator.chmod(0o755)

    runner = tmp_path / "fake_runner.sh"
    runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "%s\\n" "$1" > "${RUNNER_OUTPUT_FILE:?}"\n',
        encoding="utf-8",
    )
    runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(runner)
    env["RUNNER_OUTPUT_FILE"] = str(tmp_path / "runner_output.txt")

    scripts_dir = root_dir / "automation" / "scripts"
    scripts_dir.mkdir(parents=True)
    helper_copy = scripts_dir / "story_change_ledger.sh"
    helper_copy.write_text(LEDGER_HELPER.read_text(encoding="utf-8"), encoding="utf-8")
    helper_copy.chmod(0o755)
    validator_copy = scripts_dir / "validate_story_bundle.sh"
    validator_copy.write_text(validator.read_text(encoding="utf-8"), encoding="utf-8")
    validator_copy.chmod(0o755)

    subprocess.run(
        ["git", "init"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        ["bash", str(RUN_STORY_SCRIPT), "US-AUTO-23"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "runner_output.txt").read_text(encoding="utf-8").strip() == str(
        bundle_dir / "03_master_prompt.md"
    )

    ledger_text = (
        root_dir / "automation" / "story_change_ledger.jsonl"
    ).read_text(encoding="utf-8")
    assert '"story_id":"US-AUTO-23"' in ledger_text
    assert '"event":"story_started"' in ledger_text
    assert '"outcome":"started"' in ledger_text
    assert '"decision_source":"run_story"' in ledger_text
    assert '"artifact":"automation/bundles/active/US-AUTO-23/03_master_prompt.md"' in ledger_text


def test_run_codex_task_skips_duplicate_story_started_when_wrapper_already_recorded(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_STORY_START_LEDGER_RECORDED"] = "1"

    cmd = (
        f"source {LEDGER_HELPER} && "
        'if [[ "${AUTOMATION_STORY_START_LEDGER_RECORDED:-0}" != "1" ]]; then '
        "append_story_change_ledger_entry "
        "US-AUTO-23 story_started started '' feature/us-auto-23 '' "
        "automation/run_codex_task.sh automation/bundles/active/US-AUTO-23/03_master_prompt.md "
        "'runner started without run_story wrapper'; "
        "fi"
    )
    result = run_bash(cmd, env)

    assert result.returncode == 0, result.stderr
    assert not ledger_path.exists()


def test_run_codex_task_records_story_started_when_invoked_directly(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env.pop("AUTOMATION_STORY_START_LEDGER_RECORDED", None)

    cmd = (
        f"source {LEDGER_HELPER} && "
        'if [[ "${AUTOMATION_STORY_START_LEDGER_RECORDED:-0}" != "1" ]]; then '
        "append_story_change_ledger_entry "
        "US-AUTO-23 story_started started '' feature/us-auto-23 '' "
        "automation/run_codex_task.sh automation/bundles/active/US-AUTO-23/03_master_prompt.md "
        "'runner started without run_story wrapper'; "
        "fi"
    )
    result = run_bash(cmd, env)

    assert result.returncode == 0, result.stderr
    line = ledger_path.read_text(encoding='utf-8').strip()
    assert '"event":"story_started"' in line
    assert '"decision_source":"automation/run_codex_task.sh"' in line
    assert '"note":"runner started without run_story wrapper"' in line

def test_append_story_change_ledger_entry_writes_valid_jsonl(tmp_path: Path) -> None:
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
    line = ledger_path.read_text(encoding="utf-8").strip()

    entry = json.loads(line)
    assert entry["story_id"] == "US-AUTO-23"
    assert entry["event"] == "review_outcome"
    assert entry["outcome"] == "approve"
    assert entry["run_id"] == "2026-03-20_10-00-00"
    assert entry["branch"] == "feature/us-auto-23"
    assert entry["pr_number"] == "123"
    assert entry["decision_source"] == "review_classification"
    assert entry["artifact"] == "automation/runs/US-AUTO-23/2026-03-20_10-00-00/review_gate_result.json"
    assert entry["note"] == "review completed"


def test_append_story_change_ledger_entry_escapes_control_characters(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    cmd = (
        f"source {LEDGER_HELPER} && "
        "append_story_change_ledger_entry "
        "US-AUTO-23 review_outcome reject 2026-03-20_10-00-00 "
        "'feature/us-auto-23' '' review_classification "
        "'automation/runs/tab\tpath.json' "
        "$'line1\nline2\rline3'"
    )
    result = run_bash(cmd, env)

    assert result.returncode == 0, result.stderr

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["event"] == "review_outcome"
    assert entry["outcome"] == "reject"
    assert entry["artifact"] == "automation/runs/tab\tpath.json"
    assert entry["note"] == "line1\nline2\rline3"
