from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "classify_review_story_run.sh"
)

VALID_AI_REVIEW = "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n"


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def current_head(root_dir: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def add_commit(root_dir: Path, relative_path: str, content: str, message: str) -> str:
    target = root_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", relative_path], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root_dir, check=True, capture_output=True, text=True)
    return current_head(root_dir)


def setup_git_repo(root_dir: Path) -> None:
    root_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)
    (root_dir / "tracked.txt").write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)


def write_fake_codex(fake_bin_dir: Path, marker_file: Path) -> Path:
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' invoked > "{marker_file}"
output_file=""
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "-o" ]]; then
    output_file="$2"
    shift 2
    continue
  fi
  shift
done
cat >/dev/null
cat > "$output_file" <<'EOF'
# Review Classification

MERGE RECOMMENDATION: approve
EOF
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    return fake_codex


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


def test_classify_review_story_run_allows_manual_finish_continuation_after_non_converging_rerun(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-51"

    first_head = current_head(root_dir)
    second_head = add_commit(root_dir, "story_impl.txt", "second\n", "second head")

    previous_run = make_run_dir(root_dir, story_id, "2026-03-27_10-00-00")
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text(
        "services/story_loop.py\n"
        "tests/test_story_loop.py\n",
        encoding="utf-8",
    )

    run_dir = make_run_dir(root_dir, story_id, "2026-03-27_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {second_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
        encoding="utf-8",
    )
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")

    add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "add classification rules"], cwd=root_dir, check=True, capture_output=True, text=True)

    fake_bin_dir = tmp_path / "bin_manual_finish"
    marker_file = tmp_path / "codex_invoked_manual_finish.txt"
    write_fake_codex(fake_bin_dir, marker_file)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert marker_file.exists()
    assert "Merge recommendation: approve" in result.stdout
    assert (run_dir / "review_classification.md").exists()
    assert "review_head_mismatch" not in result.stderr


def test_classify_review_story_run_rejects_generic_stale_head_mismatch(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-51"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-27_12-20-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- starting_head: 0000000000000000000000000000000000000000\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")
    subprocess.run(["git", "add", str(rules_file.relative_to(root_dir))], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "add classification rules"], cwd=root_dir, check=True, capture_output=True, text=True)

    fake_bin_dir = tmp_path / "bin_stale"
    marker_file = tmp_path / "codex_invoked_stale.txt"
    write_fake_codex(fake_bin_dir, marker_file)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "review_head_mismatch" in result.stderr
    assert not marker_file.exists()


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
