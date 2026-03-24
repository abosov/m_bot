from pathlib import Path
import os
import subprocess


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "automation" / "scripts" / "run_story.sh"


REQUIRED_BUNDLE_FILES = [
    "00_story.md",
    "01_context_bundle.md",
    "02_file_scope.md",
    "03_master_prompt.md",
    "04_review_checklist.md",
    "05_followups.md",
    "06_manual_actions.md",
]


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def setup_repo(root_dir: Path, story_id: str) -> None:
    root_dir.mkdir(parents=True)
    run(["git", "init", "-b", "main"], cwd=root_dir)
    run(["git", "config", "user.email", "codex@example.com"], cwd=root_dir)
    run(["git", "config", "user.name", "Codex Test"], cwd=root_dir)

    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    bundle_dir.mkdir(parents=True)
    for file_name in REQUIRED_BUNDLE_FILES:
        (bundle_dir / file_name).write_text(f"# {file_name}\n", encoding="utf-8")

    pack_path = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(f"# Story Bundle Pack\nStory-ID: {story_id}\nVersion: 1\n", encoding="utf-8")

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")

    validator = root_dir / "automation" / "scripts" / "validate_story_bundle.sh"
    validator.parent.mkdir(parents=True, exist_ok=True)
    validator.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n", encoding="utf-8")
    validator.chmod(0o755)

    run(["git", "add", "."], cwd=root_dir)
    commit = run(["git", "commit", "-m", "init"], cwd=root_dir)
    assert commit.returncode == 0, commit.stderr


def test_run_story_cleans_ephemeral_ledger_on_success(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"

    status = run(["git", "status", "--porcelain", "--", "automation/story_change_ledger.jsonl"], cwd=root_dir)
    assert status.returncode == 0, status.stderr
    assert status.stdout.strip() == ""


def test_run_story_cleans_ephemeral_ledger_when_runner_fails(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    fake_runner = root_dir / "fake_runner_fail.sh"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 17\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 17
    status = run(["git", "status", "--porcelain", "--", "automation/story_change_ledger.jsonl"], cwd=root_dir)
    assert status.returncode == 0, status.stderr
    assert status.stdout.strip() == ""


def test_run_story_keeps_non_ledger_runner_changes_visible(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    fake_runner = root_dir / "fake_runner.sh"
    non_ledger_output = root_dir / "implementation_output.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' changed > {str(non_ledger_output)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert non_ledger_output.read_text(encoding="utf-8").strip() == "changed"

    ledger_status = run(
        ["git", "status", "--porcelain", "--", "automation/story_change_ledger.jsonl"],
        cwd=root_dir,
    )
    assert ledger_status.returncode == 0, ledger_status.stderr
    assert ledger_status.stdout.strip() == ""

    non_ledger_status = run(
        ["git", "status", "--porcelain", "--", "implementation_output.txt"],
        cwd=root_dir,
    )
    assert non_ledger_status.returncode == 0, non_ledger_status.stderr
    assert non_ledger_status.stdout.strip() == "?? implementation_output.txt"


def test_run_story_blocks_dirty_story_artifacts_with_commit_hint(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    bundle_story = root_dir / "automation" / "bundles" / "active" / story_id / "03_master_prompt.md"
    bundle_story.write_text("# dirty\n", encoding="utf-8")

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"ERROR: story artifacts for '{story_id}' must be committed before run:" in result.stderr
    assert f"Remediation: automation/scripts/commit_story_artifacts.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_dirty_pack_artifact_with_commit_hint(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    pack_path = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    pack_path.write_text(pack_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"ERROR: story artifacts for '{story_id}' must be committed before run:" in result.stderr
    assert f"Remediation: automation/scripts/commit_story_artifacts.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_allows_dirty_ephemeral_ledger_path(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.write_text('{"event":"story_started"}\n', encoding="utf-8")

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"


def test_run_story_blocks_when_latest_run_has_pending_escalation(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "pending",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "because escalation is required for the latest rejected run" in result.stderr
    assert "automation/scripts/escalate_story.sh" in result.stderr
    assert not runner_marker.exists()


def test_run_story_allows_force_followup_after_escalation_resolution(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"


def test_run_story_blocks_resolved_escalation_with_missing_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{"escalation_required":true,"status":"resolved"}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid resolution_action" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_empty_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid resolution_action" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_unexpected_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": "retry"\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid resolution_action" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_only_nested_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "metadata": {\n'
        '    "resolution_action": "force-followup"\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid resolution_action" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_abort_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": "abort"\n'
        '}\n',
        encoding="utf-8",
    )

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "because escalation was resolved as 'abort'" in result.stderr
    assert not runner_marker.exists()
