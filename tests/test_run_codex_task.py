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

    assert result.returncode == 0, result.stderr

    runs_root = root_dir / "automation" / "runs" / "US-AUTO-7"
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    changed_files = (run_dir / "changed_files.txt").read_text(encoding="utf-8")
    diff_patch = (run_dir / "diff.patch").read_text(encoding="utf-8")
    manifest = (run_dir / "manifest.md").read_text(encoding="utf-8")
    review_bundle = (run_dir / "review_bundle.md").read_text(encoding="utf-8")
    review_prompt = (run_dir / "chatgpt_review_prompt.md").read_text(encoding="utf-8")

    assert changed_files.strip() == "tracked.txt"
    assert "tracked.txt" in diff_patch
    assert "story change" in diff_patch
    assert "- review_base_ref: origin/main" in manifest
    assert "- review_diff_range: origin/main...HEAD" in manifest
    assert "- changed_files_detected: yes" in manifest
    assert "## Review Diff Source\norigin/main...HEAD" in review_bundle
    assert "tracked.txt" in review_bundle
    assert "- Review diff source: origin/main...HEAD" in review_prompt
