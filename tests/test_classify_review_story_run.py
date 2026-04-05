from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "classify_review_story_run.sh"
)


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


def test_classify_review_story_run_fails_closed_on_missing_normalized_ai_review_with_raw_output(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-48" / "2026-03-27_12-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-48\n", encoding="utf-8")
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\n- Finding present only in raw output\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked.txt"
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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-48"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classify_review_story_run_allows_exact_manual_finish_continuation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add classification rules"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )

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
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("stale\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
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
printf '%s\\n' '# Review Classification' > "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' 'MERGE RECOMMENDATION: approve' >> "$output"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

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
    assert "Merge recommendation: approve" in result.stdout


def test_classify_review_story_run_rejects_manual_finish_continuation_without_final_head_artifact_proof(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add classification rules"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )

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
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("stale\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

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
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classify_review_story_run_rejects_descendant_after_manual_finish_continuation(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "add classification rules"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )

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
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-55"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "review classification blocked for 'US-AUTO-55'" in result.stderr
    assert "Reviewed HEAD" in result.stderr
    assert "does not match current checkout HEAD" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classify_review_story_run_fails_closed_on_invalid_normalized_ai_review_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-48" / "2026-03-27_12-05-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-48\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text("# AI Review Result\n", encoding="utf-8")
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\n- Raw output exists for debugging\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_invalid"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_invalid.txt"
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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-48"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classify_review_story_run_fails_closed_on_prompt_echo_ai_review_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-48" / "2026-03-27_12-10-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-48\n", encoding="utf-8")
    prompt_text = (
        "# AI Review\n\n"
        "- Finding echoed from prompt.\n\n"
        "# AI Review Result\n\n"
        "PASS\n"
        "This is a long prompt line to trigger echo detection during classification validation.\n"
        "This is a long prompt line to trigger echo detection during classification validation.\n"
        "This is a long prompt line to trigger echo detection during classification validation.\n"
        "This is a long prompt line to trigger echo detection during classification validation.\n"
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(prompt_text, encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(prompt_text, encoding="utf-8")
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_echo"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_invoked_echo.txt"
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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-48"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()

def test_classify_review_story_run_allows_manual_finish_continuation_with_companion_filtered_baseline(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init ignore automation"], cwd=root_dir, check=True, capture_output=True, text=True)

    # scope: code-only
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
    subprocess.run(["git", "commit", "-m", "scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "rules"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)

    # implementation + companion change
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("impl\n", encoding="utf-8")

    registry_file = root_dir / "docs" / "90_codex" / "epics" / "US-AUTO_REGISTRY.md"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text("registry\n", encoding="utf-8")

    subprocess.run(
        ["git", "add", "services/story_loop.py", "docs/90_codex/epics/US-AUTO_REGISTRY.md"],
        cwd=root_dir,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "impl + companion"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )

    # ВАЖНО: только impl в diff
    filtered_diff = subprocess.run(
        ["git", "diff", review_artifact_base, "--", "services/story_loop.py"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-04-01_12-00-00"
    run_dir.mkdir(parents=True)

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {current_head(root_dir)}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )

    (run_dir / "diff.patch").write_text(filtered_diff, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")

    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nOK\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_called.txt"

    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' called > "{marker_file}"
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) output="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\\n' '# Review Classification' > "$output"
printf '%s\\n' 'MERGE RECOMMENDATION: approve' >> "$output"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-70"],
        cwd=root_dir,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert marker_file.exists()


def test_classify_review_story_run_rejects_manual_finish_when_filtered_diff_surface_did_not_repeat(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)
    init_git_repo(root_dir)

    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init ignore automation"], cwd=root_dir, check=True, capture_output=True, text=True)

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
    subprocess.run(["git", "commit", "-m", "scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "rules"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)
    first_head = add_commit(root_dir, "services/story_loop.py", "return 'first'\n", "first implementation")

    previous_run = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-04-01_11-00-00"
    previous_run.mkdir(parents=True)
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: US-AUTO-70\n"
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

    reviewed_head = add_commit(root_dir, "services/story_loop.py", "return 'second'\n", "second implementation")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-04-01_12-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
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
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nOK\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )

    add_commit(root_dir, "services/story_loop.py", "return 'manual-finish'\n", "manual finish")

    fake_bin_dir = tmp_path / "bin_reject_manual_finish"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_called_reject_manual_finish.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' called > "{marker_file}"
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
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

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
    assert not marker_file.exists()


def test_classify_review_story_run_blocks_companion_filtered_stale_review_surface_on_committed_head(
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
    subprocess.run(["git", "commit", "-m", "scope"], cwd=root_dir, check=True, capture_output=True, text=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "rules"], cwd=root_dir, check=True, capture_output=True, text=True)

    review_artifact_base = current_head(root_dir)
    add_commit(root_dir, "services/story_loop.py", "implementation\n", "story implementation")
    add_commit(root_dir, "docs/90_codex/epics/US-AUTO_REGISTRY.md", "registry\n", "companion update")

    run_dir = root_dir / "automation" / "runs" / "US-AUTO-70" / "2026-04-06_12-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {current_head(root_dir)}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n"
        f"- review_artifact_base: {review_artifact_base}\n",
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text("diff --git a/services/wrong.py b/services/wrong.py\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/wrong.py\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nOK\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_stale_filtered"
    fake_bin_dir.mkdir()
    marker_file = tmp_path / "codex_called_stale_filtered.txt"
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' called > \"{marker_file}\"\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

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
    assert not (run_dir / "review_classification.md").exists()
