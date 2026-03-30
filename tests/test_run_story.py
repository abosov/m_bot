from pathlib import Path
import json
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


def write_escalation_result(
    artifact_run_dir: Path,
    expected_story_id: str,
    *,
    omit_keys: set[str] | None = None,
    **overrides: object,
) -> None:
    payload: dict[str, object] = {
        "story_id": expected_story_id,
        "run_id": artifact_run_dir.name,
        "run_dir": str(artifact_run_dir),
        "gate_result": str(artifact_run_dir / "review_gate_result.json"),
        "escalation_required": True,
        "status": "pending",
        "decision_source": "repeated_reject_stagnation",
        "resolution_action": "force-followup",
    }
    payload.update(overrides)
    for key in omit_keys or set():
        payload.pop(key, None)
    (artifact_run_dir / "escalation_result.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def current_head(root_dir: Path) -> str:
    result = run(["git", "rev-parse", "HEAD"], cwd=root_dir)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def add_commit(root_dir: Path, relative_path: str, content: str, message: str) -> str:
    target = root_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    add = run(["git", "add", relative_path], cwd=root_dir)
    assert add.returncode == 0, add.stderr
    commit = run(["git", "commit", "-m", message], cwd=root_dir)
    assert commit.returncode == 0, commit.stderr
    return current_head(root_dir)


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


def test_run_story_allows_rerun_when_latest_run_does_not_cross_convergence_boundary(tmp_path: Path) -> None:
    story_id = "US-AUTO-47"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    first_head = current_head(root_dir)
    second_head = add_commit(root_dir, "src/story_impl.txt", "second\n", "second head")

    first_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_10-00-00"
    first_run_dir.mkdir(parents=True)
    (first_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (first_run_dir / "changed_files.txt").write_text(
        "services/story_a.py\n"
        "tests/test_story_a.py\n",
        encoding="utf-8",
    )

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_11-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {second_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (latest_run_dir / "changed_files.txt").write_text(
        "services/story_b.py\n"
        "tests/test_story_b.py\n",
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
    assert f"[INFO] Preflight: passed for {story_id}" in result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"


def test_run_story_blocks_non_converging_rerun_and_routes_to_manual_finish(tmp_path: Path) -> None:
    story_id = "US-AUTO-47"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    first_head = current_head(root_dir)
    second_head = add_commit(root_dir, "src/story_impl.txt", "second\n", "second head")

    first_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_10-00-00"
    first_run_dir.mkdir(parents=True)
    (first_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (first_run_dir / "changed_files.txt").write_text(
        "services/story_loop.py\n"
        "tests/test_story_loop.py\n",
        encoding="utf-8",
    )

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_11-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {second_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (latest_run_dir / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
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
    assert "latest committed-head rerun did not converge" in result.stderr
    assert "Manual finish required:" in result.stderr
    assert "Inspect pinned evidence:" in result.stderr
    assert "Do not rerun automation/scripts/run_story.sh again until manual finish is complete." in result.stderr
    assert not runner_marker.exists()


def test_run_story_allows_fresh_rerun_after_manual_finish_commit_on_newer_head(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    first_head = current_head(root_dir)
    second_head = add_commit(root_dir, "services/story_loop.py", "second\n", "second head")

    previous_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_10-00-00"
    previous_run_dir.mkdir(parents=True)
    (previous_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (previous_run_dir / "changed_files.txt").write_text(
        "services/story_loop.py\n"
        "tests/test_story_loop.py\n",
        encoding="utf-8",
    )

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-27_11-00-00"
    latest_run_dir.mkdir(parents=True)
    (latest_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {second_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (latest_run_dir / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
        encoding="utf-8",
    )

    add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")

    runner_marker = root_dir / "runner_called.txt"
    fake_runner = make_runner(
        tmp_path,
        "fake_runner_after_manual_finish.sh",
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
    assert "latest committed-head rerun did not converge" not in result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"


def test_run_story_blocks_when_latest_run_has_pending_escalation(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, status="pending", resolution_action="force-followup")

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


def test_run_story_allows_latest_run_with_valid_non_blocking_escalation_artifact(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, escalation_required=False)

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
    assert f"[INFO] Preflight: passed for {story_id}" in result.stderr
    assert runner_marker.read_text(encoding="utf-8").strip() == "called"


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
    write_escalation_result(custom_run_dir, story_id, status="pending", resolution_action="force-followup")

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


def test_run_story_blocks_escalation_with_invalid_status_value(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, status="resolved")

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
    assert "escalation resolution is invalid: invalid status" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_story_id_mismatch(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-01-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, story_id="US-AUTO-999")

    runner_marker = root_dir / "runner_called.txt"
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(
            tmp_path,
            "fake_runner.sh",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        )
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "story id mismatch" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_run_id_mismatch(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-02-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, run_id="2026-03-24_00-00-00")

    runner_marker = root_dir / "runner_called.txt"
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(
            tmp_path,
            "fake_runner.sh",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        )
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "run id mismatch" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_run_dir_mismatch(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-03-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, run_dir=str(latest_run_dir.parent / "spoofed"))

    runner_marker = root_dir / "runner_called.txt"
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(
            tmp_path,
            "fake_runner.sh",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        )
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "run dir mismatch" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_gate_result_mismatch(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-04-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, gate_result=str(latest_run_dir / "other_gate_result.json"))

    runner_marker = root_dir / "runner_called.txt"
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(
            tmp_path,
            "fake_runner.sh",
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' called > {str(runner_marker)!r}\n",
        )
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "gate result mismatch" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_missing_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, omit_keys={"resolution_action"})

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
    assert "escalation resolution is invalid: missing resolution action" in result.stderr
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
    write_escalation_result(latest_run_dir, story_id, resolution_action={"kind": "force-followup"})

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
    assert "non string resolution action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_empty_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, resolution_action="")

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
    assert "empty resolution action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_whitespace_only_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, resolution_action="   \t  ")

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
    assert "blank resolution action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_unexpected_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, resolution_action="retry")

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
    assert "invalid resolution action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_multiline_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, resolution_action="force-followup\nretry")

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
    assert "invalid resolution action" in result.stderr
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
    write_escalation_result(latest_run_dir, story_id, omit_keys={"resolution_action"}, metadata={"resolution_action": "force-followup"})

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
    assert "missing resolution action" in result.stderr
    assert "Fix the escalation artifact for this run before rerunning:" in result.stderr
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_abort_resolution_action(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-00-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, resolution_action="abort")

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
    assert not runner_marker.exists()


def test_run_story_blocks_resolved_escalation_with_missing_decision_source(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-10-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, omit_keys={"decision_source"})

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
    write_escalation_result(latest_run_dir, story_id, decision_source="manual_override")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(
        make_runner(tmp_path, "fake_runner.sh", "#!/usr/bin/env bash\nset -euo pipefail\n")
    )

    result = run(["bash", str(SCRIPT_PATH), story_id], cwd=root_dir, env=env)

    assert result.returncode != 0
    assert "invalid decision source" in result.stderr


def test_run_story_blocks_resolved_escalation_with_nested_decision_source_spoof(tmp_path: Path) -> None:
    story_id = "US-AUTO-37"
    root_dir = tmp_path / "repo"
    setup_repo(root_dir, story_id)

    latest_run_dir = root_dir / "automation" / "runs" / story_id / "2026-03-24_12-12-00"
    latest_run_dir.mkdir(parents=True)
    write_escalation_result(latest_run_dir, story_id, omit_keys={"decision_source"}, metadata={"decision_source": "repeated_reject_stagnation"})

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
        '{'
        f' "story_id": "{story_id}",'
        f' "run_id": "{latest_run_dir.name}",'
        f' "run_dir": "{latest_run_dir}",'
        f' "gate_result": "{latest_run_dir / "review_gate_result.json"}",'
        ' "escalation_required": true,'
        ' "status": "pending",'
        ' "decision_source": "repeated_reject_stagnation",'
        ' "decision_source": "manual_override",'
        ' "resolution_action": "force-followup"'
        ' }\n',
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
