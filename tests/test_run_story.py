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

    gitignore_path = root_dir / ".gitignore"
    gitignore_path.write_text("/automation/runs/*\n!/automation/runs/.gitkeep\n", encoding="utf-8")

    runs_keep = root_dir / "automation" / "runs" / ".gitkeep"
    runs_keep.parent.mkdir(parents=True, exist_ok=True)
    runs_keep.write_text("", encoding="utf-8")

    validator = root_dir / "automation" / "scripts" / "validate_story_bundle.sh"
    validator.parent.mkdir(parents=True, exist_ok=True)
    validator.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n", encoding="utf-8")
    validator.chmod(0o755)

    run(["git", "add", "."], cwd=root_dir)
    commit = run(["git", "commit", "-m", "init"], cwd=root_dir)
    assert commit.returncode == 0, commit.stderr


def make_runner(tmp_path: Path, name: str, script_body: str) -> Path:
    runner_path = tmp_path / name
    runner_path.write_text(script_body, encoding="utf-8")
    runner_path.chmod(0o755)
    return runner_path


def test_run_story_cleans_ephemeral_ledger_on_success(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert f"[INFO] Preflight: classifying dirty paths for {story_id}" in result.stderr
    assert f"[INFO] Preflight: passed for {story_id}" in result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"

    status = run(["git", "status", "--porcelain", "--", "automation/story_change_ledger.jsonl"], cwd=root_dir)
    assert status.returncode == 0, status.stderr
    assert status.stdout.strip() == ""


def test_run_story_cleans_ephemeral_ledger_when_runner_fails(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    fake_runner = make_runner(
        tmp_path,
        "fake_runner_fail.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 17\n",
    )

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

    non_ledger_output = root_dir / "implementation_output.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' changed > {str(non_ledger_output)!r}\n",
    )

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

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"[INFO] Preflight: classifying dirty paths for {story_id}" in result.stderr
    assert f"ERROR: preflight blocked for '{story_id}' because requested story artifacts are dirty:" in result.stderr
    assert "Operator handoff:" in result.stderr
    assert "Review the requested story artifact changes." in result.stderr
    assert f"Run: automation/scripts/commit_story_artifacts.sh {story_id}" in result.stderr
    assert f"Rerun: automation/scripts/run_story.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_dirty_pack_artifact_with_commit_hint(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    pack_path = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    pack_path.write_text(pack_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"[INFO] Preflight: classifying dirty paths for {story_id}" in result.stderr
    assert f"ERROR: preflight blocked for '{story_id}' because requested story artifacts are dirty:" in result.stderr
    assert "Operator handoff:" in result.stderr
    assert f"Run: automation/scripts/commit_story_artifacts.sh {story_id}" in result.stderr
    assert f"Rerun: automation/scripts/run_story.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_unrelated_dirty_paths_before_handoff(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    unrelated_path = root_dir / "notes.txt"
    unrelated_path.write_text("dirty\n", encoding="utf-8")

    bundle_story = root_dir / "automation" / "bundles" / "active" / story_id / "03_master_prompt.md"
    bundle_story.write_text("# dirty\n", encoding="utf-8")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"[INFO] Preflight: classifying dirty paths for {story_id}" in result.stderr
    assert f"ERROR: preflight blocked for '{story_id}' because unrelated dirty paths exist:" in result.stderr
    assert " - notes.txt" in result.stderr
    assert "Requested story artifact paths also remain dirty:" in result.stderr
    assert f" - automation/bundles/active/{story_id}/03_master_prompt.md" in result.stderr
    assert "Resolve unrelated changes outside the story-artifact handoff flow." in result.stderr
    assert f"Then rerun: automation/scripts/run_story.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_unrelated_dirty_paths_without_story_artifact_handoff(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    unrelated_path = root_dir / "notes.txt"
    unrelated_path.write_text("dirty\n", encoding="utf-8")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert f"[INFO] Preflight: classifying dirty paths for {story_id}" in result.stderr
    assert f"ERROR: preflight blocked for '{story_id}' because unrelated dirty paths exist:" in result.stderr
    assert " - notes.txt" in result.stderr
    assert "Requested story artifact paths also remain dirty:" not in result.stderr
    assert "Operator handoff:" not in result.stderr
    assert "Resolve unrelated changes outside the story-artifact handoff flow." in result.stderr
    assert f"Then rerun: automation/scripts/run_story.sh {story_id}" in result.stderr
    assert not runner_marker.exists()


def test_run_story_allows_dirty_ephemeral_ledger_path(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.write_text('{"event":"story_started"}\n', encoding="utf-8")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "because escalation is required for the latest rejected run" in result.stderr
    assert "automation/scripts/escalate_story.sh" in result.stderr
    assert not runner_marker.exists()


def test_run_story_honors_automation_runs_root_for_escalation(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    default_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_11-00-00"
    default_run_dir.mkdir(parents=True)
    (default_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": false,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    custom_runs_root = tmp_path / "tmp_runs"
    custom_run_dir = custom_runs_root / story_id / "2026-03-24_12-00-00"
    custom_run_dir.mkdir(parents=True)
    (custom_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "pending",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)
    env["AUTOMATION_RUNS_ROOT"] = str(custom_runs_root)

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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

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
        '{"escalation_required":true,"status":"resolved","decision_source":"repeated_reject_stagnation"}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "escalation resolution is invalid: missing resolution_action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_malformed_json(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text("{\n", encoding="utf-8")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "escalation resolution is invalid: malformed json" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_non_string_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": {"kind": "force-followup"}\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "non-string resolution_action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "empty resolution_action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_whitespace_only_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": "   \\t  "\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "whitespace-only resolution_action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": "retry"\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert 'unknown resolution_action "retry"' in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_multiline_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": "force-followup\\nretry"\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert 'unknown resolution_action "force-followup\\nretry"' in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_when_manifest_declares_missing_escalation_artifact(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "manifest.md").write_text(
        "# Manifest\n\n"
        "## Artifacts\n"
        "- manifest.md\n"
        "- escalation_result.json\n",
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "escalation resolution is invalid: missing required escalation artifact" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "metadata": {\n'
        '    "resolution_action": "force-followup"\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "missing resolution_action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
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
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "resolution_action": "abort"\n'
        '}\n',
        encoding="utf-8",
    )

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner.sh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' called > {str(runner_marker)!r}\n",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "because escalation was resolved as 'abort'" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_missing_decision_source(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-10-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(tmp_path, "fake_runner.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "missing decision source" in result.stderr


def test_run_story_blocks_resolved_escalation_with_wrong_decision_source(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-11-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "decision_source": "manual_override",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(tmp_path, "fake_runner.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid decision_source 'manual_override'" in result.stderr


def test_run_story_blocks_resolved_escalation_with_nested_decision_source_spoof(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-12-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "metadata": {\n'
        '    "decision_source": "repeated_reject_stagnation"\n'
        '  },\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(tmp_path, "fake_runner.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "missing decision source" in result.stderr


def test_run_story_blocks_resolved_escalation_with_duplicate_decision_source_keys(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-13-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "decision_source": "repeated_reject_stagnation", "decision_source": "manual_override", "resolution_action": "force-followup" }\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(tmp_path, "fake_runner.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "escalation resolution is invalid: duplicate key" in result.stderr
