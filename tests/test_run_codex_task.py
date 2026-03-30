from pathlib import Path
import os
import shutil
import signal
import subprocess
import time


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


def fake_codex_script(body: str) -> str:
    return f"""#!/usr/bin/env bash
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
{body}
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
"""


def latest_run_dir(root_dir: Path, story_id: str = "US-AUTO-7") -> Path:
    runs_root = root_dir / "automation" / "runs" / story_id
    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def assert_story_run_artifacts_exist(root_dir: Path, story_id: str = "US-AUTO-7") -> Path:
    runs_root = root_dir / "automation" / "runs" / story_id
    assert runs_root.exists()
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

    bundle_dir = (
        root_dir
        / "automation"
        / "bundles"
        / "active"
        / "US-AUTO-7"
    )
    prompt_file = bundle_dir / "03_master_prompt.md"
    scope_file = bundle_dir / "02_file_scope.md"
    bundle_dir.mkdir(parents=True)
    prompt_file.write_text("# Prompt\n\nRun the workflow.\n", encoding="utf-8")
    scope_file.write_text(
        """# US-AUTO-7: File Scope

## Files Allowed To Change
- `tracked.txt`
- `generated/from_worktree.txt`
- `reports/materialized.txt`
- `tests/test_materialized_state.py`

## Files Not Allowed To Change
- `backend/**`

## Scope Notes
- Minimal test scope for run_codex_task integration tests.
""",
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
if [[ -n "${FAKE_CODEX_STDIN_FILE:-}" ]]; then
  cat > "$FAKE_CODEX_STDIN_FILE"
else
  cat >/dev/null
fi
if [[ -n "${workdir:-}" ]]; then
  printf '%s\\n' 'codex isolated edit' >> "$workdir/tracked.txt"
  mkdir -p "$workdir/generated"
  printf '%s\\n' 'materialized file' > "$workdir/generated/from_worktree.txt"
fi
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
    env["FAKE_CODEX_STDIN_FILE"] = str(tmp_path / "codex_stdin.txt")

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
    repository_map_runtime = (run_dir / "repository_map_runtime.md").read_text(encoding="utf-8")
    story_context = (run_dir / "story_context.md").read_text(encoding="utf-8")
    codex_prompt = (run_dir / "codex_prompt.md").read_text(encoding="utf-8")
    review_bundle = (run_dir / "review_bundle.md").read_text(encoding="utf-8")
    review_prompt = (run_dir / "chatgpt_review_prompt.md").read_text(encoding="utf-8")
    pytest_output = (run_dir / "pytest.txt").read_text(encoding="utf-8")
    codex_cwd = Path((tmp_path / "codex_cwd.txt").read_text(encoding="utf-8").strip())
    codex_stdin = (tmp_path / "codex_stdin.txt").read_text(encoding="utf-8")

    assert changed_files.splitlines() == [
        "generated/from_worktree.txt",
        "tests/test_materialized_state.py",
        "tracked.txt",
    ]
    assert "tracked.txt" in diff_patch
    assert "codex isolated edit" in diff_patch
    assert "generated/from_worktree.txt" in diff_patch
    assert "diff --git a/generated/from_worktree.txt b/generated/from_worktree.txt" in diff_patch
    assert str(root_dir / "generated" / "from_worktree.txt") not in diff_patch
    assert "generated/from_worktree.txt" in diff_stat
    assert "- review_base_ref: origin/main" in manifest
    assert "- review_diff_range: origin/main...HEAD" in manifest
    assert "- review_artifact_base:" in manifest
    assert "- changed_files_detected: yes" in manifest
    assert "- repository_map_runtime_file:" in manifest
    assert "- repository_map_injection_status: injected" in manifest
    assert (
        "- repository_map_source_docs: "
        "docs/40_ai/zumbot_codex/REPOSITORY_MAP.md,"
        "docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md"
    ) in manifest
    assert "- isolated_run: yes" in manifest
    assert "- isolated_worktree_dir:" in manifest
    assert "- isolated_worktree_head:" in manifest
    assert "- materialization_status: applied" in manifest
    assert "- materialized_tracked_changes: 1" in manifest
    assert "- materialized_untracked_files: 1" in manifest
    assert "isolated_run=true" in meta
    assert "repository_map_runtime_file=" in meta
    assert "repository_map_injection_status=injected" in meta
    assert "isolated_worktree_dir=" in meta
    assert "isolated_worktree_head=" in meta
    assert "# Repository Map Runtime" in repository_map_runtime
    assert "## Architecture Layers" in repository_map_runtime
    assert (
        "- API/Application: transport, validation, orchestration; "
        "keep business rules out."
    ) in repository_map_runtime
    assert "## Story-Local Context" in repository_map_runtime
    assert "- story_id: US-AUTO-7" in repository_map_runtime
    assert "- active_bundle_path: automation/bundles/active/US-AUTO-7" in repository_map_runtime
    assert "- scope_file: automation/bundles/active/US-AUTO-7/02_file_scope.md" in repository_map_runtime
    assert "- bundle_status: present" in repository_map_runtime
    assert "- scope_parse_status: parsed" in repository_map_runtime
    assert "- files_not_allowed_parse_status: parsed" in repository_map_runtime
    assert "- story_scope_constraints: loaded" in repository_map_runtime
    assert "- files_allowed_to_change:" in repository_map_runtime
    assert "- tracked.txt" in repository_map_runtime
    assert "- generated/from_worktree.txt" in repository_map_runtime
    assert "- reports/materialized.txt" in repository_map_runtime
    assert "- tests/test_materialized_state.py" in repository_map_runtime
    assert "- files_not_allowed_to_change:" in repository_map_runtime
    assert "- backend/**" in repository_map_runtime
    assert "## Anti-Hallucination Rules" in repository_map_runtime
    assert "- Do not invent files, modules, services, migrations, or tests" in repository_map_runtime
    assert "## Pipeline Dependency Hints" in repository_map_runtime
    assert "- This artifact is generated by automation/run_codex_task.sh before Codex execution." in repository_map_runtime
    assert "Curated project context." in repository_map_runtime
    assert "Curated repository map." in repository_map_runtime
    assert "Repository map artifact:" in story_context
    assert "- repository_map_runtime.md" in story_context
    assert "Repository map artifact: repository_map_runtime.md" in codex_prompt
    assert "Curated repository map." in codex_prompt
    assert "# Prompt" in codex_prompt
    assert codex_stdin == codex_prompt
    assert codex_cwd != root_dir
    assert codex_cwd.name.startswith("zumbot-codex-worktree-")
    assert not codex_cwd.exists()
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == (
        "base\nstory change\ncodex isolated edit\n"
    )
    assert (root_dir / "generated" / "from_worktree.txt").read_text(encoding="utf-8") == (
        "materialized file\n"
    )
    assert "## Review Diff Source\norigin/main...HEAD (merge-base " in review_bundle
    assert "tracked.txt" in review_bundle
    assert "generated/from_worktree.txt" in review_bundle
    assert "1 passed" in pytest_output
    assert "- Review diff source: origin/main...HEAD" in review_prompt
    assert "- Review artifact base:" in review_prompt
    assert "## Required output format" in review_prompt
    assert "Return only a markdown document in exactly this structure." in review_prompt
    assert "# AI Review" in review_prompt
    assert "# AI Review Result" in review_prompt
    assert "The first non-empty line must be exactly:" in review_prompt
    assert "Under # AI Review Result, output exactly one of:" in review_prompt
    assert "Do not output anything before # AI Review." in review_prompt

def test_run_codex_task_marks_scope_parse_status_missing(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    scope_file = (
        root_dir
        / "automation"
        / "bundles"
        / "active"
        / "US-AUTO-7"
        / "02_file_scope.md"
    )
    scope_file.unlink()
    run(["git", "add", "-A"], cwd=root_dir)
    run(["git", "commit", "-m", "Remove scope file"], cwd=root_dir)

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

    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""


def test_run_codex_task_ignores_committed_same_story_bundle_artifacts_during_scope_validation(
    tmp_path: Path,
) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    bundle_pack = root_dir / "automation" / "bundle_packs" / "US-AUTO-7.bundle.md"
    bundle_pack.parent.mkdir(parents=True)
    bundle_pack.write_text("# Bundle Pack\n\nCommitted canonical artifact.\n", encoding="utf-8")
    run(["git", "add", "automation/bundle_packs/US-AUTO-7.bundle.md"], cwd=root_dir)
    run(["git", "commit", "-m", "Add canonical bundle artifact"], cwd=root_dir)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    write_executable(
        fake_bin_dir / "codex",
        fake_codex_script("printf '%s\\n' 'codex isolated edit' >> \"$workdir/tracked.txt\""),
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

    assert changed_files.splitlines() == ["tracked.txt"]
    assert "automation/bundle_packs/US-AUTO-7.bundle.md" not in changed_files


def test_run_codex_task_marks_scope_parse_status_unparseable(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    scope_file = (
        root_dir
        / "automation"
        / "bundles"
        / "active"
        / "US-AUTO-7"
        / "02_file_scope.md"
    )
    scope_file.write_text(
        """# US-AUTO-7: File Scope



## Unexpected Allowed Heading
- `tracked.txt`

## Unexpected Blocked Heading
- `backend/**`
""",
        encoding="utf-8",
    )
    run(["git", "add", "automation/bundles/active/US-AUTO-7/02_file_scope.md"], cwd=root_dir)
    run(["git", "commit", "-m", "Make scope file unparseable"], cwd=root_dir)

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

    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""

def test_run_codex_task_marks_scope_parse_status_unparseable_when_blocked_scope_list_is_missing(
    tmp_path: Path,
) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    scope_file = (
        root_dir
        / "automation"
        / "bundles"
        / "active"
        / "US-AUTO-7"
        / "02_file_scope.md"
    )
    scope_file.write_text(
        """# US-AUTO-7: File Scope

## Files Allowed To Change
- `tracked.txt`
- `automation/bundles/active/US-AUTO-7/02_file_scope.md`

## Scope Notes
- Missing forbidden section on purpose.
""",
        encoding="utf-8",
    )
    run(["git", "add", "automation/bundles/active/US-AUTO-7/02_file_scope.md"], cwd=root_dir)
    run(["git", "commit", "-m", "Make scope file partially parseable"], cwd=root_dir)

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
    repository_map_runtime = (run_dir / "repository_map_runtime.md").read_text(encoding="utf-8")

    assert "- scope_parse_status: parsed" in repository_map_runtime
    assert "- files_not_allowed_parse_status: unavailable" in repository_map_runtime
    assert "- story_scope_constraints: loaded" in repository_map_runtime
    assert "- files_allowed_to_change:" in repository_map_runtime
    assert "- tracked.txt" in repository_map_runtime
    assert "- automation/bundles/active/US-AUTO-7/02_file_scope.md" in repository_map_runtime
    assert "- files_not_allowed_to_change:\n  unavailable" in repository_map_runtime


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

    assert result.returncode == 42, result.stderr

    codex_cwd = Path((tmp_path / "codex_cwd_failure.txt").read_text(encoding="utf-8").strip())
    assert codex_cwd.name.startswith("zumbot-codex-worktree-")
    assert not codex_cwd.exists()
    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "codex_last_message.txt").exists() or (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""


def test_run_codex_task_rolls_back_changes_when_codex_exits_non_zero(tmp_path: Path) -> None:
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

    assert result.returncode == 23, result.stderr
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == "base\nstory change\n"
    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""


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
    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""


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


def test_run_codex_task_rejects_real_out_of_scope_implementation_change(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    write_executable(
        fake_bin_dir / "codex",
        fake_codex_script(
            "mkdir -p \"$workdir/backend\"\nprintf '%s\\n' 'rogue change' > \"$workdir/backend/out_of_scope.py\""
        ),
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
    assert "ERROR: changed files outside allowed scope for story US-AUTO-7:" in result.stderr
    assert "backend/out_of_scope.py" in result.stderr


def test_run_codex_task_treats_sigterm_as_failure_and_rolls_back(tmp_path: Path) -> None:
    root_dir, prompt_file = setup_story_repo(tmp_path)

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    started_file = tmp_path / "codex_started.txt"
    write_executable(
        fake_bin_dir / "codex",
        f"""#!/usr/bin/env bash
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
printf '%s\\n' "$workdir" > {str(started_file)!r}
trap 'exit 143' TERM
cat >/dev/null &
wait
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"

    process = subprocess.Popen(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    deadline = time.time() + 5
    while time.time() < deadline and not started_file.exists():
      time.sleep(0.05)

    assert started_file.exists()

    os.killpg(process.pid, signal.SIGTERM)
    stdout, stderr = process.communicate(timeout=5)

    assert "preserving run artifacts at:" in stdout
    assert process.returncode == 143, stderr
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == "base\nstory change\n"
    run_dir = assert_story_run_artifacts_exist(root_dir)
    assert (run_dir / "run_meta.txt").exists()
    status = run(["git", "status", "--porcelain"], cwd=root_dir)
    assert status.stdout.strip() == ""


def test_run_codex_task_surfaces_rollback_failure(tmp_path: Path) -> None:
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
printf '%s\\n' 'rollback should fail' >> "$workdir/tracked.txt"
cat >/dev/null
printf '%s\\n' 'codex summary' > "$output"
exit 23
""",
    )
    real_git = shutil.which("git")
    assert real_git is not None
    write_executable(
        fake_bin_dir / "git",
        f"""#!/usr/bin/env bash
set -euo pipefail
if [[ "${{FAIL_ROLLBACK_RESTORE:-0}}" == "1" && "${{1:-}}" == "-C" && "${{3:-}}" == "restore" ]]; then
  exit 55
fi
exec {real_git!r} "$@"
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["SKIP_PYTEST"] = "1"
    env["FAIL_ROLLBACK_RESTORE"] = "1"

    result = run(
        ["bash", str(SCRIPT_PATH), str(prompt_file)],
        cwd=root_dir,
        env=env,
        check=False,
    )

    assert result.returncode == 1
    assert "ERROR: automatic rollback failed" in result.stderr
    assert "ERROR: tracked restore failed with exit code 55" in result.stderr
    assert (root_dir / "tracked.txt").read_text(encoding="utf-8") == (
        "base\nstory change\nrollback should fail\n"
    )
