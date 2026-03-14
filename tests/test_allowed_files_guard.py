from pathlib import Path
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "automation" / "scripts" / "check_allowed_files.sh"
RUN_SCRIPT = ROOT / "automation" / "run_codex_task.sh"


def run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def write_scope(bundle_dir: Path, allowed_lines: list[str]) -> None:
    scope_lines = [
        "# Scope",
        "",
        "## Files Allowed To Change",
        *allowed_lines,
        "",
        "## Files Not Allowed To Change",
        "- `backend/**`",
    ]
    (bundle_dir / "02_file_scope.md").write_text(
        "\n".join(scope_lines) + "\n",
        encoding="utf-8",
    )


def setup_guard_bundle(tmp_path: Path, story_id: str = "US-AUTO-14") -> tuple[Path, Path]:
    repo_dir = tmp_path / "repo"
    bundle_dir = repo_dir / "automation" / "bundles" / "active" / story_id
    bundle_dir.mkdir(parents=True)
    return repo_dir, bundle_dir


def test_check_allowed_files_exact_path_allowed(tmp_path: Path) -> None:
    repo_dir, bundle_dir = setup_guard_bundle(tmp_path)
    write_scope(
        bundle_dir,
        [
            "",
            "- `automation/run_codex_task.sh`",
            "",
        ],
    )
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("automation/run_codex_task.sh\n", encoding="utf-8")

    result = run(
        ["bash", str(CHECK_SCRIPT), "US-AUTO-14", str(changed_files), str(bundle_dir)],
        cwd=repo_dir,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_check_allowed_files_recursive_directory_allowed(tmp_path: Path) -> None:
    repo_dir, bundle_dir = setup_guard_bundle(tmp_path)
    write_scope(bundle_dir, ["- `automation/bundles/active/US-AUTO-14/**`"])
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text(
        "automation/bundles/active/US-AUTO-14/03_master_prompt.md\n",
        encoding="utf-8",
    )

    result = run(
        ["bash", str(CHECK_SCRIPT), "US-AUTO-14", str(changed_files), str(bundle_dir)],
        cwd=repo_dir,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_check_allowed_files_reports_violation(tmp_path: Path) -> None:
    repo_dir, bundle_dir = setup_guard_bundle(tmp_path)
    write_scope(bundle_dir, ["- `automation/run_codex_task.sh`"])
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("backend/app.py\n", encoding="utf-8")

    result = run(
        ["bash", str(CHECK_SCRIPT), "US-AUTO-14", str(changed_files), str(bundle_dir)],
        cwd=repo_dir,
        check=False,
    )

    assert result.returncode != 0
    assert "changed files outside allowed scope for story US-AUTO-14" in result.stderr
    assert "backend/app.py" in result.stderr


def test_check_allowed_files_accepts_empty_change_list(tmp_path: Path) -> None:
    repo_dir, bundle_dir = setup_guard_bundle(tmp_path)
    write_scope(bundle_dir, ["- `automation/run_codex_task.sh`"])
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("", encoding="utf-8")

    result = run(
        ["bash", str(CHECK_SCRIPT), "US-AUTO-14", str(changed_files), str(bundle_dir)],
        cwd=repo_dir,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_check_allowed_files_rejects_missing_allowed_rules(tmp_path: Path) -> None:
    repo_dir, bundle_dir = setup_guard_bundle(tmp_path)
    (bundle_dir / "02_file_scope.md").write_text(
        "# Scope\n\n## Files Allowed To Change\n\n## Files Not Allowed To Change\n- `backend/**`\n",
        encoding="utf-8",
    )
    changed_files = tmp_path / "changed_files.txt"
    changed_files.write_text("", encoding="utf-8")

    result = run(
        ["bash", str(CHECK_SCRIPT), "US-AUTO-14", str(changed_files), str(bundle_dir)],
        cwd=repo_dir,
        check=False,
    )

    assert result.returncode != 0
    assert "no allowed file patterns found" in result.stderr


def setup_story_repo(tmp_path: Path) -> tuple[Path, Path]:
    root_dir = tmp_path / "repo"
    origin_dir = tmp_path / "origin.git"

    root_dir.mkdir()
    run(["git", "init", "-b", "main"], cwd=root_dir)
    run(["git", "config", "user.name", "Test User"], cwd=root_dir)
    run(["git", "config", "user.email", "test@example.com"], cwd=root_dir)

    prompt_file = (
        root_dir
        / "automation"
        / "bundles"
        / "active"
        / "US-AUTO-14"
        / "03_master_prompt.md"
    )
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("# Prompt\n\nRun the workflow.\n", encoding="utf-8")
    write_scope(prompt_file.parent, ["- `automation/run_codex_task.sh`"])
    scripts_dir = root_dir / "automation" / "scripts"
    scripts_dir.mkdir(parents=True)
    (root_dir / "automation" / "run_codex_task.sh").write_text(
        RUN_SCRIPT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "check_allowed_files.sh").write_text(
        CHECK_SCRIPT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    docs_dir = root_dir / "docs" / "40_ai" / "zumbot_codex"
    docs_dir.mkdir(parents=True)
    (docs_dir / "PROJECT_CONTEXT.md").write_text(
        "# Project Context\n\nCurated project context.\n",
        encoding="utf-8",
    )
    (docs_dir / "REPOSITORY_MAP.md").write_text(
        "# Repository Map\n\nCurated repository map.\n",
        encoding="utf-8",
    )

    tracked_file = root_dir / "tracked.txt"
    tracked_file.write_text("base\n", encoding="utf-8")

    run(["git", "add", "."], cwd=root_dir)
    run(["git", "commit", "-m", "Initial main commit"], cwd=root_dir)

    run(["git", "init", "--bare", str(origin_dir)], cwd=root_dir)
    run(["git", "remote", "add", "origin", str(origin_dir)], cwd=root_dir)
    run(["git", "push", "-u", "origin", "main"], cwd=root_dir)
    run(["git", "fetch", "origin", "main"], cwd=root_dir)
    run(["git", "checkout", "-b", "feat/us-auto-14-guard"], cwd=root_dir)

    return root_dir, prompt_file


def latest_run_dir(root_dir: Path, story_id: str = "US-AUTO-14") -> Path:
    runs_root = root_dir / "automation" / "runs" / story_id
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def test_run_codex_task_blocks_pytest_before_execution_on_scope_violation(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    write_executable(
        fake_bin_dir / "codex",
        """#!/usr/bin/env bash
set -euo pipefail
output=""
workdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      output="$2"
      shift 2
      ;;
    -C)
      workdir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$workdir/frontend"
printf '%s\\n' 'violation' > "$workdir/frontend/out_of_scope.txt"
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
""",
    )
    write_executable(
        fake_bin_dir / "pytest",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' 'pytest ran' >> "${PYTEST_MARKER_FILE:?}"
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["PYTEST_MARKER_FILE"] = str(tmp_path / "pytest_marker.txt")

    result = run(
        ["bash", str(RUN_SCRIPT), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "changed files outside allowed scope for story US-AUTO-14" in result.stderr
    assert "frontend/out_of_scope.txt" in result.stderr
    assert not Path(env["PYTEST_MARKER_FILE"]).exists()

    run_dir = latest_run_dir(root_dir)
    changed_files = (run_dir / "changed_files.txt").read_text(encoding="utf-8")
    assert "frontend/out_of_scope.txt" in changed_files
def test_run_codex_task_fails_when_scope_file_is_missing(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    scope_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-14" / "02_file_scope.md"
    scope_file.unlink()
    run(["git", "add", "-A"], cwd=root_dir)
    run(["git", "commit", "-m", "Remove scope file for regression test"], cwd=root_dir)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()

    write_executable(
        fake_bin_dir / "codex",
        """#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      output="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
""",
    )

    write_executable(
        fake_bin_dir / "pytest",
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' 'pytest ran' >> "${PYTEST_MARKER_FILE:?}"
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["PYTEST_MARKER_FILE"] = str(tmp_path / "pytest_marker.txt")

    result = run(
        ["bash", str(RUN_SCRIPT), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "scope file is missing" in result.stderr.lower() or "scope file not found" in result.stderr.lower()
    assert not Path(env["PYTEST_MARKER_FILE"]).exists()