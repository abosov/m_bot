import json
import os
from pathlib import Path
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "refresh_review_evidence.sh"
)
ANALYZE_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "analyze_story_run.sh"
)


def init_repo(
    root_dir: Path,
    *,
    branch: str = "feature/us-auto-60",
    with_origin: bool = True,
) -> None:
    root_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)
    (root_dir / ".gitignore").write_text("automation/runs/\n", encoding="utf-8")
    (root_dir / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    if with_origin:
        origin_dir = root_dir.parent / "origin.git"
        subprocess.run(["git", "init", "--bare", str(origin_dir)], cwd=root_dir, check=True, capture_output=True, text=True)
        subprocess.run(["git", "remote", "add", "origin", str(origin_dir)], cwd=root_dir, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=root_dir, check=True, capture_output=True, text=True)

    if branch != "main":
        subprocess.run(["git", "checkout", "-b", branch], cwd=root_dir, check=True, capture_output=True, text=True)


def current_head(root_dir: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root_dir, check=True, capture_output=True, text=True).stdout.strip()


def write_story_bundle(root_dir: Path, story_id: str) -> None:
    scope = root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md"
    scope.parent.mkdir(parents=True, exist_ok=True)
    scope.write_text(
        "# Scope\n\n## Files Allowed To Change\n- `automation/scripts/refresh_review_evidence.sh`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(scope.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", f"add scope {story_id}"], cwd=root_dir, check=True, capture_output=True, text=True)


def run_refresh(root_dir: Path, story_id: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_REFRESH_PYTEST_CMD"] = "python3 -c 'print(\"refresh pytest ok\")'"
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        cwd=root_dir,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def latest_run_dir(root_dir: Path, story_id: str) -> Path:
    story_root = root_dir / "automation" / "runs" / story_id
    return sorted(path for path in story_root.iterdir() if path.is_dir())[-1]


def test_refresh_review_evidence_succeeds_and_writes_metadata_without_codex_invocation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir)
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)

    marker = root_dir / "codex_invoked.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "codex").write_text(
        f"#!/usr/bin/env bash\nset -euo pipefail\nprintf 'invoked\\n' > '{marker}'\n",
        encoding="utf-8",
    )
    (fake_bin / "codex").chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_REFRESH_PYTEST_CMD"] = "python3 -c 'print(\"refresh pytest ok\")'"
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        cwd=root_dir,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    run_dir = latest_run_dir(root_dir, story_id)
    metadata = json.loads((run_dir / "refresh_review_evidence.json").read_text(encoding="utf-8"))
    assert metadata["codex_invoked"] is False
    assert metadata["current_head"] == current_head(root_dir)
    assert metadata["story_id"] == story_id
    assert "pytest_exit_code: 0" in (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "refresh pytest ok" in (run_dir / "pytest.txt").read_text(encoding="utf-8")
    assert (run_dir / "changed_files.txt").exists()
    assert (run_dir / "diff.patch").exists()
    prompt = (run_dir / "chatgpt_review_prompt.md").read_text(encoding="utf-8")
    assert "Review this Zumbot Codex change." in prompt
    assert "Pinned run directory:" in prompt
    assert str(run_dir) in prompt
    assert f"{run_dir}/refresh_review_evidence.json" in prompt
    assert f"{run_dir}/diff.patch" in prompt
    assert f"{run_dir}/changed_files.txt" in prompt
    assert "Do not use automation/output unless it points to this exact pinned run." in prompt
    assert "no-Codex review-evidence refresh run" in prompt
    assert "# AI Review" in prompt
    assert "# AI Review Result" in prompt
    assert not marker.exists()


def test_refresh_review_evidence_rejects_dirty_tree(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir)
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)
    (root_dir / "README.md").write_text("dirty\n", encoding="utf-8")

    result = run_refresh(root_dir, story_id)
    assert result.returncode != 0
    assert "working tree is dirty" in result.stderr


def test_refresh_review_evidence_rejects_missing_origin_remote(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir, with_origin=False)
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)

    result = run_refresh(root_dir, story_id)
    assert result.returncode != 0
    assert "origin remote is required" in result.stderr


def test_refresh_review_evidence_rejects_missing_refresh_pytest_command(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir)
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env.pop("AUTOMATION_REFRESH_PYTEST_CMD", None)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        cwd=root_dir,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "AUTOMATION_REFRESH_PYTEST_CMD is required" in result.stderr


def test_refresh_review_evidence_rejects_main_branch(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir, branch="main")
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)

    result = run_refresh(root_dir, story_id)
    assert result.returncode != 0
    assert "forbidden on main branch" in result.stderr


def test_refreshed_evidence_becomes_stale_after_new_commit(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir)
    story_id = "US-AUTO-60"
    write_story_bundle(root_dir, story_id)
    refresh_result = run_refresh(root_dir, story_id)
    assert refresh_result.returncode == 0, refresh_result.stderr
    run_dir = latest_run_dir(root_dir, story_id)

    (root_dir / "services").mkdir(parents=True, exist_ok=True)
    (root_dir / "services" / "changed.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "services/changed.py"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "new commit"], cwd=root_dir, check=True, capture_output=True, text=True)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    analyze_result = subprocess.run(
        ["bash", str(ANALYZE_SCRIPT_PATH), story_id],
        cwd=root_dir,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert analyze_result.returncode == 0, analyze_result.stderr
    assert "Current stage: blocked_stale_run_evidence" in analyze_result.stdout


def test_refresh_review_evidence_blocks_same_head_stage_loop_cap(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    init_repo(root_dir)
    story_id = "US-AUTO-58"
    write_story_bundle(root_dir, story_id)
    head = current_head(root_dir)

    for run_id in [
        "2026-05-02_12-00-00_refresh",
        "2026-05-02_12-10-00_refresh",
        "2026-05-02_12-20-00_refresh",
    ]:
        run_dir = root_dir / "automation" / "runs" / story_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.md").write_text(
            "# Refresh Manifest\n\n"
            f"- story_id: {story_id}\n"
            f"- starting_head: {head}\n"
            f"- isolated_worktree_head: {head}\n"
            "- review_artifact_base: HEAD\n"
            "- changed_files_detected: yes\n"
            "- pytest_exit_code: 0\n"
            "- refresh_mode: no_codex_review_evidence_refresh\n",
            encoding="utf-8",
        )
        (run_dir / "changed_files.txt").write_text("README.md\n", encoding="utf-8")
        (run_dir / "diff.patch").write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")
        (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
        (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
        (run_dir / "pytest.txt").write_text("refresh-only\n", encoding="utf-8")
        (run_dir / "refresh_review_evidence.json").write_text(
            json.dumps(
                {
                    "story_id": story_id,
                    "current_head": head,
                    "current_branch": "feature/us-auto-58",
                    "base_ref": "main",
                    "merge_base": head,
                    "refresh_mode": "no_codex_review_evidence_refresh",
                    "codex_invoked": False,
                    "generated_at": "2026-05-02T10:00:00Z",
                    "evidence_paths": {
                        "run_dir": str(run_dir),
                        "changed_files": str(run_dir / "changed_files.txt"),
                        "diff_patch": str(run_dir / "diff.patch"),
                        "manifest": str(run_dir / "manifest.md"),
                        "review_bundle": str(run_dir / "review_bundle.md"),
                        "chatgpt_review_prompt": str(run_dir / "chatgpt_review_prompt.md"),
                        "pytest": str(run_dir / "pytest.txt"),
                        "refresh_review_evidence": str(run_dir / "refresh_review_evidence.json"),
                    },
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "ai_review_result.md").write_text("# AI Review\n\nFinding\n\n# AI Review Result\n\nPASS\n", encoding="utf-8")
        (run_dir / "review_classification.md").write_text(
            "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
            encoding="utf-8",
        )

    result = run_refresh(root_dir, story_id)

    assert result.returncode != 0
    assert "same-HEAD stage loop cap is already reached" in result.stderr
    assert "LOOP CAP: REACHED" in result.stderr
    assert "analyze_story_run.sh" in result.stderr
