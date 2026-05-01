from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "ai_review_story_run.sh"
)

VALID_AI_REVIEW = "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n"


def init_git_repo(root_dir: Path) -> None:
    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)


def current_head(root_dir: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def add_commit(root_dir: Path, relative_path: str, content: str, message: str) -> str:
    path = root_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", relative_path], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root_dir, check=True, capture_output=True, text=True)
    return current_head(root_dir)

def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir

def write_required_review_artifacts(
    run_dir: Path,
    root_dir: Path,
    *,
    review_artifact_base: str | None = None,
) -> None:
    artifact_base = review_artifact_base or current_head(root_dir)

    diff_patch = subprocess.run(
        ["git", "diff", artifact_base, "--", ".", ":(exclude)automation/story_change_ledger.jsonl"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    changed_files_output = subprocess.run(
        ["git", "diff", "--name-only", artifact_base, "--", ".", ":(exclude)automation/story_change_ledger.jsonl"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    changed_files = sorted({line for line in changed_files_output.splitlines() if line.strip()})

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text(
        "\n".join(changed_files) + ("\n" if changed_files else ""),
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")

def test_ai_review_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_ai_review_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_ai_review_story_run_accepts_relative_run_dir_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-00-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-5\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
printf '%s\\n' '# AI Review' > "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '- Finding A' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '# AI Review Result' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' 'PASS' >> "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = os.path.relpath(run_dir, root_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert "AI review result written:" in result.stdout
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == VALID_AI_REVIEW
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_rejects_manifest_story_id_mismatch_for_run_override(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-05-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-99\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "AUTOMATION_RUN_DIR manifest story_id 'US-AUTO-99'" in result.stderr


def test_ai_review_story_run_allows_exact_manual_finish_continuation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "services/story_loop.py", "implementation\n", "story implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_10-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (previous_run / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (previous_run / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (previous_run / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_11-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    (run_dir / "manifest.md").write_text(
        (run_dir / "manifest.md").read_text(encoding="utf-8") + "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )

    add_commit(root_dir, "services/story_loop.py", "implementation\nmanual finish\n", "manual finish")
    changed_files = sorted(
        subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    (run_dir / "changed_files.txt").write_text(
        "".join(f"{path}\n" for path in changed_files),
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", "HEAD~1"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_manual_finish"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_manual_finish.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
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
printf '%s\\n' invoked > "{marker_file}"
cat >/dev/null
printf '%s\\n' '# AI Review' > "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '- Finding A' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '# AI Review Result' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' 'PASS' >> "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-55"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert marker_file.exists()
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == VALID_AI_REVIEW


def test_ai_review_story_run_rejects_manual_finish_continuation_without_final_head_artifact_proof(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "services/story_loop.py", "implementation\n", "story implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_10-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_11-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )
    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")

    fake_bin_dir = tmp_path / "bin_manual_finish_reject"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_manual_finish_reject.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' invoked > "{marker_file}"
exit 0
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-55"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "final-HEAD compliance" in result.stderr
    assert "review_changed_files_mismatch" in result.stderr
    assert not marker_file.exists()


def test_ai_review_story_run_allows_manual_finish_continuation_with_companion_filtered_baseline(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    scope_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-70" / "02_file_scope.md"
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(
        "# Scope\n\n"
        "## Files Allowed To Change\n"
        "- `services/story_loop.py`\n\n"
        "## Files Not Allowed To Change\n"
        "- `backend/**`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-f", str(scope_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "add code-only scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)
    first_head = add_commit(root_dir, "services/story_loop.py", "implementation\n", "story implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-03-27_10-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-70\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (previous_run / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, first_head, "--", "services/story_loop.py"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    reviewed_head = add_commit(
        root_dir,
        "docs/90_codex/epics/US-AUTO_REGISTRY.md",
        "# registry\n",
        "companion-only rerun",
    )

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-03-27_11-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-70\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    registry_file = root_dir / "docs" / "90_codex" / "epics" / "US-AUTO_REGISTRY.md"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    (root_dir / "services" / "story_loop.py").write_text("implementation\nmanual finish\n", encoding="utf-8")
    registry_file.write_text("# registry\nmanual finish\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "services/story_loop.py", "docs/90_codex/epics/US-AUTO_REGISTRY.md"],
        cwd=root_dir,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "manual finish with companion registry update"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, "--", "services/story_loop.py"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_manual_finish_companion"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_manual_finish_companion.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
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
printf '%s\\n' invoked > "{marker_file}"
cat >/dev/null
printf '%s\\n' '# AI Review' > "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '- Finding A' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '# AI Review Result' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' 'PASS' >> "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-70"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert marker_file.exists()
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == VALID_AI_REVIEW


def test_ai_review_story_run_rejects_manual_finish_when_filtered_diff_surface_did_not_repeat(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    scope_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-70" / "02_file_scope.md"
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(
        "# Scope\n\n"
        "## Files Allowed To Change\n"
        "- `services/story_loop.py`\n\n"
        "## Files Not Allowed To Change\n"
        "- `backend/**`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-f", str(scope_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "add code-only scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)
    first_head = add_commit(root_dir, "services/story_loop.py", "return 'first'\n", "story implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-03-27_10-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-70\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (previous_run / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, first_head, "--", "services/story_loop.py"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    reviewed_head = add_commit(
        root_dir,
        "services/story_loop.py",
        "return 'second'\n",
        "second implementation rerun",
    )

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-03-27_11-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-70\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    (run_dir / "review_bundle.md").write_text("artifact\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("artifact\n", encoding="utf-8")
    (run_dir / "pytest.txt").write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, reviewed_head, "--", "services/story_loop.py"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )

    add_commit(root_dir, "services/story_loop.py", "return 'manual-finish'\n", "manual finish")

    fake_bin_dir = tmp_path / "bin_manual_finish_reject"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-70"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "does not match current checkout HEAD" in result.stderr


def test_ai_review_story_run_blocks_companion_filtered_stale_review_surface_on_committed_head(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "ignore automation"], cwd=root_dir, check=True, capture_output=True, text=True)

    scope_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-70" / "02_file_scope.md"
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(
        "# Scope\n\n"
        "## Files Allowed To Change\n"
        "- `services/story_loop.py`\n\n"
        "## Files Not Allowed To Change\n"
        "- `backend/**`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-f", str(scope_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "add code-only scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)
    add_commit(root_dir, "services/story_loop.py", "implementation\n", "story implementation")
    add_commit(root_dir, "docs/90_codex/epics/US-AUTO_REGISTRY.md", "registry\n", "companion update")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-04-06_12-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-70\n"
        f"- starting_head: {current_head(root_dir)}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    for artifact_name in ["review_bundle.md", "chatgpt_review_prompt.md", "pytest.txt"]:
        (run_dir / artifact_name).write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/wrong.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/services/wrong.py b/services/wrong.py\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_stale_filtered"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_stale_filtered.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' invoked > \"{marker_file}\"\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-70"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "filtered review artifacts are stale or inconsistent with recomputed baseline" in result.stderr
    assert not marker_file.exists()


def test_ai_review_story_run_rejects_descendant_after_manual_finish_continuation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "story_impl.txt", "implementation\n", "story implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_10-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-55" / "2026-03-27_11-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-55\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text("artifact\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")
    add_commit(root_dir, "followup.txt", "descendant\n", "descendant after manual finish")

    fake_bin_dir = tmp_path / "bin_descendant"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_descendant.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' invoked > "{marker_file}"
exit 0
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-55"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "AI review blocked for 'US-AUTO-55'" in result.stderr
    assert "Reviewed HEAD" in result.stderr
    assert "does not match current checkout HEAD" in result.stderr
    assert not marker_file.exists()


def test_ai_review_story_run_rejects_incomplete_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-10-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_incomplete"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
printf '%s\\n' '# AI Review Result' > "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_rejects_malformed_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-15-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_malformed"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
printf '%s\\n' 'raw text without expected heading' > "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()


def test_ai_review_story_run_rejects_unreadable_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-20-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_unreadable"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
python3 - "$output" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_bytes(b"\\xff\\xfe\\x00\\x00")
PY
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_normalizes_raw_output_when_result_file_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-25-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_raw_only"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding recovered from raw output'
printf '%s\\n' ''
printf '%s\\n' '# AI Review Result'
printf '%s\\n' ''
printf '%s\\n' 'PASS'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == (
        "# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )


def test_ai_review_story_run_fails_closed_when_raw_output_cannot_be_normalized(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-30-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_raw_invalid"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' 'plain text without normalized heading'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "plain text without normalized heading\n"
    )


def test_ai_review_story_run_recovers_invalid_result_from_normalizable_raw_output(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-35-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_invalid_result_recovered"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
printf '%s\\n' '# AI Review Result' > "$output"
printf '%s\\n' 'preamble before normalized review'
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding recovered from raw output'
printf '%s\\n' ''
printf '%s\\n' '# AI Review Result'
printf '%s\\n' ''
printf '%s\\n' 'PASS'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "preamble before normalized review\n# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )


def test_ai_review_story_run_rejects_prompt_echo_output(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-40-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    prompt_text = (
        "# AI Review\n\n"
        "- Finding echoed from prompt.\n\n"
        "# AI Review Result\n\n"
        "PASS\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(prompt_text, encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_echo"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
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
cat "{run_dir / 'chatgpt_review_prompt.md'}" > "$output"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()


def test_ai_review_story_run_rejects_output_missing_required_sections(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-45-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_missing_section"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding without required result section'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()

def test_ai_review_rejects_invalid_projection(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    story_id = "US-AUTO-75"
    run_dir = make_run_dir(root_dir, story_id, "ai-invalid-projection")

    review_artifact_base = current_head(root_dir)
    add_commit(root_dir, "impl.txt", "implementation\n", "add implementation")
    source_head = current_head(root_dir)

    write_required_review_artifacts(
        run_dir,
        root_dir,
        review_artifact_base=review_artifact_base,
    )

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {source_head}\n"
        f"- review_artifact_base: {review_artifact_base}\n"
        "- execution_companion_filter_mode: enabled\n",
        encoding="utf-8",
    )

    (run_dir / "semantic_projection.json").write_text("{invalid\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_invalid_projection"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_invalid_projection.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' invoked > "{marker_file}"
exit 0
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "semantic projection" in result.stderr.lower()
    assert not marker_file.exists()