from pathlib import Path
import os
import subprocess


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "automation" / "run_codex_task.sh"


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


def latest_run_dir(root_dir: Path, story_id: str = "US-AUTO-7") -> Path:
    runs_root = root_dir / "automation" / "runs" / story_id
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    assert len(run_dirs) == 1
    return run_dirs[0]


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
        / "US-AUTO-7"
        / "03_master_prompt.md"
    )
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("# Prompt\n\nRun the workflow.\n", encoding="utf-8")

    tracked_file = root_dir / "tracked.txt"
    tracked_file.write_text("base\n", encoding="utf-8")

    run(["git", "add", "."], cwd=root_dir)
    run(["git", "commit", "-m", "Initial main commit"], cwd=root_dir)

    run(["git", "init", "--bare", str(origin_dir)], cwd=root_dir)
    run(["git", "remote", "add", "origin", str(origin_dir)], cwd=root_dir)
    run(["git", "push", "-u", "origin", "main"], cwd=root_dir)
    run(["git", "fetch", "origin", "main"], cwd=root_dir)

    run(["git", "checkout", "-b", "feat/us-auto-7-stable-review"], cwd=root_dir)
    tracked_file.write_text("base\nstory change\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], cwd=root_dir)
    run(["git", "commit", "-m", "Story change"], cwd=root_dir)

    return root_dir, prompt_file


def test_run_codex_task_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_run_codex_task_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_run_codex_task_uses_commit_range_review_evidence(tmp_path: Path) -> None:
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
if [[ -n "${FAKE_CODEX_CWD_FILE:-}" ]]; then
  printf '%s\\n' "$workdir" > "$FAKE_CODEX_CWD_FILE"
fi
if [[ -n "${workdir:-}" ]]; then
  printf '%s\\n' 'codex isolated edit' >> "$workdir/tracked.txt"
  mkdir -p "$workdir/generated"
  printf '%s\\n' 'materialized file' > "$workdir/generated/from_worktree.txt"
fi
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
""",
    )
    (root_dir / "tests").mkdir()
    (
        root_dir / "tests" / "test_materialized_state.py"
    ).write_text(
        """
from pathlib import Path


def test_materialized_primary_checkout_state() -> None:
    assert Path("tracked.txt").read_text(encoding="utf-8").endswith("codex isolated edit\\n")
    assert Path("generated/from_worktree.txt").read_text(encoding="utf-8") == "materialized file\\n"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    run(["git", "add", "tests/test_materialized_state.py"], cwd=root_dir)
    run(["git", "commit", "-m", "Add pytest verification test"], cwd=root_dir)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["FAKE_CODEX_CWD_FILE"] = str(tmp_path / "codex_cwd.txt")

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    run_dir = latest_run_dir(root_dir)

    changed_files = (run_dir / "changed_files.txt").read_text(encoding="utf-8")
    diff_patch = (run_dir / "diff.patch").read_text(encoding="utf-8")
    diff_stat = (run_dir / "diff.stat").read_text(encoding="utf-8")
    manifest = (run_dir / "manifest.md").read_text(encoding="utf-8")
    meta = (run_dir / "run_meta.txt").read_text(encoding="utf-8")
    review_bundle = (run_dir / "review_bundle.md").read_text(encoding="utf-8")
    review_prompt = (run_dir / "chatgpt_review_prompt.md").read_text(encoding="utf-8")
    pytest_output = (run_dir / "pytest.txt").read_text(encoding="utf-8")
    codex_cwd = Path((tmp_path / "codex_cwd.txt").read_text(encoding="utf-8").strip())

    assert changed_files.splitlines() == [
        "generated/from_worktree.txt",
        "tests/test_materialized_state.py",
        "tracked.txt",
    ]
    assert "tracked.txt" in diff_patch
    assert "codex isolated edit" in diff_patch
    assert "generated/from_worktree.txt" in diff_patch
    assert "generated/from_worktree.txt" in diff_stat
    assert "- review_base_ref: origin/main" in manifest
    assert "- review_diff_range: origin/main...HEAD" in manifest
    assert "- review_artifact_base:" in manifest
    assert "- changed_files_detected: yes" in manifest
    assert "- isolated_run: yes" in manifest
    assert "- isolated_worktree_dir:" in manifest
    assert "- isolated_worktree_head:" in manifest
    assert "- materialization_status: applied" in manifest
    assert "- materialized_tracked_changes: 1" in manifest
    assert "- materialized_untracked_files: 1" in manifest
    assert "isolated_run=true" in meta
    assert "isolated_worktree_dir=" in meta
    assert "isolated_worktree_head=" in meta
    assert codex_cwd != root_dir
    assert codex_cwd.name.startswith("zumbot-codex-worktree-")
    assert not codex_cwd.exists()
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == (
        "base\nstory change\ncodex isolated edit\n"
    )
    assert (root_dir / "generated" / "from_worktree.txt").read_text(encoding="utf-8") == (
        "materialized file\n"
    )
    assert "## Review Diff Source\norigin/main... working tree (merge-base " in review_bundle
    assert "tracked.txt" in review_bundle
    assert "generated/from_worktree.txt" in review_bundle
    assert "1 passed" in pytest_output
    assert "- Review diff source: origin/main...HEAD" in review_prompt
    assert "- Review artifact base:" in review_prompt


def test_run_codex_task_cleans_up_worktree_when_codex_fails(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    write_executable(
        fake_bin_dir / "codex",
        """#!/usr/bin/env bash
set -euo pipefail
workdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -C)
      workdir="$2"
      shift 2
      ;;
    -o)
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
if [[ -n "${FAKE_CODEX_CWD_FILE:-}" ]]; then
  printf '%s\\n' "$workdir" > "$FAKE_CODEX_CWD_FILE"
fi
cat >/dev/null
exit 42
""",
    )
    write_executable(
        fake_bin_dir / "pytest",
        "#!/usr/bin/env bash\nexit 0\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"
    env["FAKE_CODEX_CWD_FILE"] = str(tmp_path / "codex_cwd_failure.txt")

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    codex_cwd = Path((tmp_path / "codex_cwd_failure.txt").read_text(encoding="utf-8").strip())
    assert codex_cwd.name.startswith("zumbot-codex-worktree-")
    assert not codex_cwd.exists()


def test_run_codex_task_materializes_changes_when_codex_exits_non_zero(tmp_path: Path) -> None:
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
printf '%s\\n' 'non-zero run with changes' >> "$workdir/tracked.txt"
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
exit 23
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == (
        "base\nstory change\nnon-zero run with changes\n"
    )

    manifest = (latest_run_dir(root_dir) / "manifest.md").read_text(encoding="utf-8")
    assert "- codex_exit_code: 23" in manifest
    assert "- materialization_status: applied" in manifest
    assert "- materialized_tracked_changes: 1" in manifest


def test_run_codex_task_fails_when_expected_materialization_does_not_reach_primary_checkout(
    tmp_path: Path,
) -> None:
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
mkdir -p "$workdir/generated"
printf '%s\\n' 'should fail to materialize' > "$workdir/generated/missing.txt"
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
""",
    )
    write_executable(
        fake_bin_dir / "cp",
        "#!/usr/bin/env bash\nexit 0\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode != 0
    assert "materialization missing untracked path in primary checkout: generated/missing.txt" in result.stderr
    assert not (root_dir / "generated" / "missing.txt").exists()


def test_run_codex_task_records_materialized_untracked_files_in_artifacts(tmp_path: Path) -> None:
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
mkdir -p "$workdir/reports"
printf '%s\\n' 'artifact body' > "$workdir/reports/materialized.txt"
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    run_dir = latest_run_dir(root_dir)
    changed_files = (run_dir / "changed_files.txt").read_text(encoding="utf-8")
    diff_patch = (run_dir / "diff.patch").read_text(encoding="utf-8")
    diff_stat = (run_dir / "diff.stat").read_text(encoding="utf-8")

    assert changed_files.splitlines() == ["reports/materialized.txt", "tracked.txt"]
    assert "reports/materialized.txt" in diff_patch
    assert "artifact body" in diff_patch
    assert "Untracked files materialized into primary checkout:" in diff_stat
    assert "reports/materialized.txt" in diff_stat
