# file: tests/test_review_story_run.py
from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "review_story_run.sh"
)


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def setup_git_repo(root_dir: Path) -> None:
    root_dir.mkdir(parents=True)
    subprocess.run(["git", "init"], check=True, cwd=root_dir, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex Test"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    (root_dir / ".gitignore").write_text(
        "/automation/runs/*\n!/automation/runs/.gitkeep\n",
        encoding="utf-8",
    )
    (root_dir / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "README.md"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )


def write_artifacts(run_dir: Path, *, include_manifest: bool = True) -> None:
    artifact_names = [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]
    if include_manifest:
        artifact_names.insert(0, "manifest.md")

    for artifact_name in artifact_names:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")


def test_review_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_review_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_review_story_run_reports_latest_run_with_manifest(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    older_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_10-00-00")
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(older_run_dir)
    write_artifacts(latest_run_dir)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert f"Latest run: {latest_run_dir}" in result.stdout
    assert f" - {latest_run_dir / 'manifest.md'}" in result.stdout
    assert "Review safety: SAFE" in result.stdout
    assert (
        f"Workflow helper (source of truth): AUTOMATION_RUN_DIR={latest_run_dir} "
        "automation/scripts/analyze_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        f"Deterministic gate command: AUTOMATION_RUN_DIR={latest_run_dir} "
        "automation/scripts/review_gate_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        "Use analyze_story_run.sh to determine current stage, resume safety, "
        "and next recommended command."
    ) in result.stdout
    assert "does not enforce workflow transitions" in result.stdout


def test_review_story_run_fails_when_manifest_is_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir, include_manifest=False)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "manifest.md" in result.stderr


def test_review_story_run_blocks_when_working_tree_is_dirty(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir)
    (root_dir / "README.md").write_text("dirty change\n", encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Review safety: BLOCKED" in result.stdout
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stdout
    assert "commit the changes if they belong in the reviewed diff, or discard them if they do not" in result.stdout
    assert f"AUTOMATION_RUN_DIR={latest_run_dir}" in result.stdout
    assert "analyze_story_run.sh US-AUTO-21" in result.stdout
    assert "follow the next recommended command from analyze output" in result.stdout
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stderr


def test_review_story_run_ignores_ephemeral_ledger_dirty_state(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "add", "automation/story_change_ledger.jsonl"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "track ledger"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    ledger_path.write_text('{"dirty":true}\n', encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Review safety: SAFE" in result.stdout
    assert "Review safety: BLOCKED" not in result.stdout


def test_review_story_run_accepts_relative_run_dir_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    older_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_10-00-00")
    selected_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(older_run_dir)
    write_artifacts(selected_run_dir)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = os.path.relpath(selected_run_dir, root_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert f"Latest run: {selected_run_dir}" in result.stdout
    assert (
        f"Workflow helper (source of truth): AUTOMATION_RUN_DIR={selected_run_dir} "
        "automation/scripts/analyze_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        f"Deterministic gate command: AUTOMATION_RUN_DIR={selected_run_dir} "
        "automation/scripts/review_gate_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        "Use analyze_story_run.sh to determine current stage, resume safety, "
        "and next recommended command."
    ) in result.stdout
    assert "does not enforce workflow transitions" in result.stdout
