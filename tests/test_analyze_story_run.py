from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "analyze_story_run.sh"
)

VALID_AI_REVIEW = "# AI Review\n\n- Finding A\n"


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def run_script(root_dir: Path, story_id: str, *, run_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    if run_dir is not None:
        env["AUTOMATION_RUN_DIR"] = str(run_dir)

    return subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_analyze_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_analyze_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_analyze_story_run_summarizes_latest_run_and_gate_status(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_11-00-00")
    make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_10-00-00")

    (latest_run_dir / "run_meta.txt").write_text(
        "story_id=US-AUTO-19\nrun_id=2026-03-16_11-00-00\n",
        encoding="utf-8",
    )
    (latest_run_dir / "diff.stat").write_text(
        " automation/scripts/analyze_story_run.sh | 10 +++++++++-\n",
        encoding="utf-8",
    )
    (latest_run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- starting_head: abc1234\n"
        "- review_base_ref: origin/main\n"
        "- materialization_status: applied\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (latest_run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n"
        "tests/test_analyze_story_run.py\n"
        "docs/90_codex/STORY_EXECUTION_CHECKLIST.md\n"
        "automation/bundles/active/US-AUTO-19/03_master_prompt.md\n",
        encoding="utf-8",
    )
    (latest_run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n"
        "collected 4 items\n"
        "4 passed\n",
        encoding="utf-8",
    )
    (latest_run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (latest_run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )
    (latest_run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "approve",\n'
        '  "status": "passed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19")

    assert result.returncode == 0, result.stderr
    assert f"Run: {latest_run_dir.name}" in result.stdout
    assert f"Directory: {latest_run_dir}" in result.stdout
    assert "run_meta.txt: yes" in result.stdout
    assert "diff.stat: yes" in result.stdout
    assert "Branch: feature/us-auto-19" in result.stdout
    assert (
        "Changed Files\n"
        "4 files (automation/scripts/analyze_story_run.sh, "
        "tests/test_analyze_story_run.py, docs/90_codex/STORY_EXECUTION_CHECKLIST.md, ...)"
    ) in result.stdout
    assert "Pytest\npass (exit 0; 4 passed)" in result.stdout
    assert "Classification: present (approve)" in result.stdout
    assert "Gate: present (approve/passed via review_classification)" in result.stdout
    assert "RUN STATUS: READY FOR MERGE REVIEW (gate approve)" not in result.stdout
    assert "RUN STATUS: BLOCKED (cannot verify run evidence: checkout HEAD unavailable)" in result.stdout


def test_analyze_story_run_blocks_merge_ready_status_when_gate_approved_but_working_tree_dirty(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    tracked.write_text("dirty\n", encoding="utf-8")

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_11-05-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- review_base_ref: origin/main\n"
        "- materialization_status: applied\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n"
        "collected 4 items\n"
        "4 passed\n",
        encoding="utf-8",
    )
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "approve",\n'
        '  "status": "passed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Gate: present (approve/passed via review_classification)" in result.stdout
    assert "RUN STATUS: READY FOR MERGE REVIEW" not in result.stdout
    assert (
        "RUN STATUS: BLOCKED (workspace-only changes detected; commit or discard them before "
        "review/classify/gate because those steps operate on committed HEAD only)"
    ) in result.stdout


def test_analyze_story_run_tolerates_missing_artifacts_and_incomplete_runs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_12-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- changed_files_detected: no\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nNo valid merge recommendation yet.\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "changed_files.txt: no" in result.stdout
    assert "pytest.txt: no" in result.stdout
    assert "Changed Files\nmissing" in result.stdout
    assert "Pytest\nmissing" in result.stdout
    assert "Classification: present (invalid)" in result.stdout
    assert "Gate: missing" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout
    assert "RUN STATUS: CHECK RUN OUTPUT (no changed files detected)" not in result.stdout


def test_analyze_story_run_rejects_split_line_recommendation_for_gate_parity(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_16-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "5. Merge recommendation\n"
        "- `approve`\n\n"
        "MERGE RECOMMENDATION\n"
        "approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (invalid)" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout


def test_analyze_story_run_accepts_same_line_recommendation_format(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_16-05-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\n"
        "MERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (approve)" in result.stdout
    assert "Classification: present (invalid recommendation)" not in result.stdout
    assert "RUN STATUS: READY TO RUN GATE (pinned artifacts ready; classification approve)" in result.stdout


def test_analyze_story_run_marks_malformed_recommendation_as_invalid(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_16-10-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\n"
        "MERGE RECOMMENDATION maybe approve later\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (invalid)" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout


def test_analyze_story_run_blocks_on_pytest_failure_before_review_follow_up(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_13-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 1\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("1 failed\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Pytest\nfail (exit 1; 1 failed)" in result.stdout
    assert "AI review: present" in result.stdout
    assert "RUN STATUS: BLOCKED (pytest failing)" in result.stdout
    assert "RUN STATUS: READY TO CLASSIFY" not in result.stdout


def test_analyze_story_run_surfaces_invalid_ai_review_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_13-05-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text("# AI Review Result\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "AI review: present (invalid: ai_review_incomplete_artifact)" in result.stdout
    assert "Current stage: blocked_ai_review_invalid" in result.stdout
    assert "Latest valid stage: run_artifacts_ready" in result.stdout
    assert "RUN STATUS: CHECK AI REVIEW OUTPUT (invalid artifact: ai_review_incomplete_artifact)" in result.stdout
    assert "RUN STATUS: READY TO CLASSIFY" not in result.stdout


def test_analyze_story_run_surfaces_unreadable_ai_review_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_13-06-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_bytes(b"\xff\xfe\x00\x00")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "AI review: present (invalid: ai_review_unreadable_artifact)" in result.stdout
    assert "Current stage: blocked_ai_review_invalid" in result.stdout
    assert "Latest valid stage: run_artifacts_ready" in result.stdout
    assert "RUN STATUS: CHECK AI REVIEW OUTPUT (invalid artifact: ai_review_unreadable_artifact)" in result.stdout
    assert "RUN STATUS: READY TO CLASSIFY" not in result.stdout


def test_analyze_story_run_marks_missing_manifest_fields_as_unknown(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_14-00-00")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Branch: unknown" in result.stdout
    assert "Starting HEAD: unknown" in result.stdout
    assert "Review Base: unknown" in result.stdout
    assert "Codex exit: unknown" in result.stdout


def test_analyze_story_run_fails_on_invalid_story_id() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "invalid-story"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "invalid STORY_ID 'invalid-story'" in result.stderr


def test_analyze_story_run_fails_when_story_root_is_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"

    result = run_script(root_dir, "US-AUTO-19")

    assert result.returncode != 0
    assert "story run root not found for 'US-AUTO-19'" in result.stderr


def test_analyze_story_run_rejects_parent_dir_escape_in_run_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_14-00-00")
    make_run_dir(root_dir, "US-AUTO-21", "2026-03-16_15-00-00")

    escaped = Path("automation/runs/US-AUTO-19/../US-AUTO-21/2026-03-16_15-00-00")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-19"],
        cwd=root_dir,
        env={
            **os.environ,
            "AUTOMATION_ROOT_DIR": str(root_dir),
            "AUTOMATION_RUN_DIR": str(escaped),
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "AUTOMATION_RUN_DIR must be inside story run root" in result.stderr


def test_analyze_story_run_rejects_manifest_story_id_mismatch(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_14-00-00")
    manifest = run_dir / "manifest.md"
    manifest.write_text(
        "# Codex Run Manifest\n\n"
        "- story_id: US-AUTO-21\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode != 0
    assert "manifest story_id 'US-AUTO-21' does not match requested story 'US-AUTO-19'" in result.stderr


def test_analyze_story_run_surfaces_codex_failure_status(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_17-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 1\n"
        "- changed_files_detected: no\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Codex exit: 1" in result.stdout
    assert "RUN STATUS: BLOCKED (codex failing)" in result.stdout


def test_analyze_story_run_surfaces_materialization_failure_status(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_17-10-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: failed\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Materialization: failed" in result.stdout
    assert "RUN STATUS: BLOCKED (materialization failed)" in result.stdout


def test_analyze_story_run_blocks_ready_actions_when_working_tree_dirty(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    tracked.write_text("dirty\n", encoding="utf-8")

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_17-20-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n"
        "collected 4 items\n"
        "4 passed\n",
        encoding="utf-8",
    )
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: blocked_dirty_working_tree" in result.stdout
    assert "Latest valid stage: classification_approved" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert (
        "RUN STATUS: BLOCKED (workspace-only changes detected; commit or discard them before "
        "review/classify/gate because those steps operate on committed HEAD only)"
    ) in result.stdout


def test_analyze_story_run_blocks_ready_actions_when_untracked_file_exists(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    untracked = root_dir / "new_untracked.txt"
    untracked.write_text("dirty\n", encoding="utf-8")

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_17-25-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n"
        "collected 4 items\n"
        "4 passed\n",
        encoding="utf-8",
    )
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert (
        "RUN STATUS: BLOCKED (workspace-only changes detected; commit or discard them before "
        "review/classify/gate because those steps operate on committed HEAD only)"
    ) in result.stdout


def test_analyze_story_run_ignores_ephemeral_ledger_dirty_state(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/runs/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "add", "automation/story_change_ledger.jsonl"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "commit", "-m", "track ledger"], cwd=root_dir, check=True, capture_output=True, text=True)
    ledger_path.write_text('{"event":"story_started"}\n', encoding="utf-8")

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_17-30-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: classification_approved" in result.stdout
    assert "Latest valid stage: classification_approved" in result.stdout
    assert "Resume safety: safe" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE (pinned artifacts ready; classification approve)" in result.stdout
    assert (
        "RUN STATUS: BLOCKED (workspace-only changes detected; commit or discard them before "
        "review/classify/gate because those steps operate on committed HEAD only)"
    ) not in result.stdout


def test_analyze_story_run_surfaces_missing_review_prerequisites(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Review prerequisites: missing (review_bundle.md,chatgpt_review_prompt.md,diff.patch)" in result.stdout
    assert "AI review: missing (prerequisites review_bundle.md,chatgpt_review_prompt.md,diff.patch)" in result.stdout
    assert "RUN STATUS: BLOCKED (missing review prerequisites: review_bundle.md,chatgpt_review_prompt.md,diff.patch)" in result.stdout


def test_analyze_story_run_surfaces_ai_review_raw_failure_without_result_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-05-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_raw_output.txt").write_text("codex exec failed\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Review prerequisites: ready" in result.stdout
    assert "AI review: failed (raw output only)" in result.stdout
    assert "RUN STATUS: BLOCKED (ai review failed; inspect ai_review_raw_output.txt)" in result.stdout


def test_analyze_story_run_pytest_summary_has_clean_stderr(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-20-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n"
        "collected 4 items\n"
        "4 passed\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Pytest\npass (exit 0; 4 passed)" in result.stdout
    assert result.stderr == ""


def test_analyze_story_run_review_prerequisites_match_ai_review_contract(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-30-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )

    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Review prerequisites: missing (changed_files.txt,pytest.txt)" in result.stdout
    assert "AI review: missing (prerequisites changed_files.txt,pytest.txt)" in result.stdout
    assert "RUN STATUS: BLOCKED (missing review prerequisites: changed_files.txt,pytest.txt)" in result.stdout

def test_analyze_story_run_blocks_gate_ready_when_classification_approved_but_review_prereqs_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_21-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (approve)" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert "RUN STATUS: BLOCKED (missing review prerequisites: review_bundle.md,chatgpt_review_prompt.md,diff.patch)" in result.stdout



def test_analyze_story_run_blocks_merge_ready_when_manifest_head_is_stale(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    stale_head = "0" * 40

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_22-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {stale_head}\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "approve",\n'
        '  "status": "passed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Evidence HEAD Consistency: stale" in result.stdout
    assert f"checkout {current_head}" in result.stdout
    assert "RUN STATUS: READY FOR MERGE REVIEW" not in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert (
        "RUN STATUS: BLOCKED "
        f"(stale run evidence: manifest HEAD {stale_head} != current HEAD {current_head})"
    ) in result.stdout


def test_analyze_story_run_blocks_ready_states_when_manifest_source_of_truth_head_is_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_22-03-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "approve",\n'
        '  "status": "passed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Evidence HEAD Consistency: unknown (manifest source-of-truth HEAD missing)" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert "RUN STATUS: READY FOR MERGE REVIEW" not in result.stdout
    assert "RUN STATUS: BLOCKED (cannot verify run evidence: manifest source-of-truth HEAD missing)" in result.stdout


def test_analyze_story_run_blocks_gate_ready_when_classification_approved_but_manifest_head_is_stale(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    stale_head = "f" * 40

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_22-05-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {stale_head}\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (approve)" in result.stdout
    assert "RUN STATUS: READY TO RUN GATE" not in result.stdout
    assert (
        "RUN STATUS: BLOCKED "
        f"(stale run evidence: manifest HEAD {stale_head} != current HEAD {current_head})"
    ) in result.stdout


def test_analyze_story_run_accepts_short_starting_head_when_isolated_worktree_head_matches(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    short_head = current_head[:7]

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_22-06-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {short_head}\n"
        f"- isolated_worktree_head: {current_head}\n"
        "- codex_exit_code: 0\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert f"Starting HEAD: {short_head}" in result.stdout
    assert "Evidence HEAD Consistency: match" in result.stdout
    assert "stale run evidence" not in result.stdout
    assert "RUN STATUS: READY TO RUN GATE (pinned artifacts ready; classification approve)" in result.stdout

def test_analyze_story_run_rejects_dash_separator_recommendation_format(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-40-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "MERGE RECOMMENDATION - approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (invalid)" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout

def test_analyze_story_run_rejects_space_separator_recommendation_format(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_19-45-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "MERGE RECOMMENDATION approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (invalid)" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout


def test_analyze_story_run_reports_resume_stage_and_next_command_for_classification(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Workflow Chaining / Resume" in result.stdout
    assert "Current stage: ai_review_completed" in result.stdout
    assert "Latest valid stage: ai_review_completed" in result.stdout
    assert "Resume safety: safe" in result.stdout
    assert "AUTOMATION_RUN_DIR=" in result.stdout
    assert str(run_dir) in result.stdout
    assert "automation/scripts/classify_review_story_run.sh US-AUTO-19" in result.stdout


def test_analyze_story_run_reports_resume_next_gate_command_when_classification_approved(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-05-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: classification_approved" in result.stdout
    assert "Latest valid stage: classification_approved" in result.stdout
    assert "Resume safety: safe" in result.stdout
    assert "automation/scripts/review_gate_story_run.sh US-AUTO-19" in result.stdout


def test_analyze_story_run_reports_blocked_classification_reject_with_latest_valid_stage(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-06-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: blocked_classification_rejected" in result.stdout
    assert "Latest valid stage: ai_review_completed" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "Blocked reason: classification merge recommendation is reject" in result.stdout


def test_analyze_story_run_reports_gate_reject_as_blocked_with_latest_valid_stage(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-07-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "reject",\n'
        '  "status": "failed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: blocked_review_gate_rejected" in result.stdout
    assert "Latest valid stage: classification_approved" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "Blocked reason: gate decision reject/failed via review_classification" in result.stdout


def test_analyze_story_run_reports_pending_escalation_and_resolution_command(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-07-10")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "reject",\n'
        '  "status": "failed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "escalation_required": true,\n'
        '  "status": "pending",\n'
        '  "reason": "Repeated review_classification reject with identical diff.patch and changed_files.txt as run 2026-03-16_23-07-00",\n'
        '  "resolution_action": ""\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "escalation_result.json: yes" in result.stdout
    assert "Escalation: present (pending:" in result.stdout
    assert "Current stage: blocked_escalation_required" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "automation/scripts/escalate_story.sh US-AUTO-19 <accept-as-is|force-followup|abort>" in result.stdout
    assert "RUN STATUS: BLOCKED (escalation required; repeated reject stagnation)" in result.stdout


def test_analyze_story_run_reports_force_followup_resolution_as_resumable(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-07-11")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "reject",\n'
        '  "status": "failed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "reason": "Repeated review_classification reject with identical diff.patch and changed_files.txt as run 2026-03-16_23-07-00",\n'
        '  "resolution_action": "force-followup"\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Escalation: present (resolved via force-followup)" in result.stdout
    assert "Current stage: escalation_force_followup_resolved" in result.stdout
    assert "Resume safety: safe" in result.stdout
    assert "Next recommended command: automation/scripts/run_story.sh US-AUTO-19" in result.stdout
    assert "RUN STATUS: READY TO RUN FOLLOW-UP (escalation resolved: force-followup)" in result.stdout


def test_analyze_story_run_reports_nested_resolution_action_spoof_as_invalid(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_12-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-28\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(VALID_AI_REVIEW, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )
    (run_dir / "review_gate_result.json").write_text(
        '{\n'
        '  "decision": "reject",\n'
        '  "status": "failed",\n'
        '  "decision_source": "review_classification"\n'
        '}\n',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{\n'
        '  "decision_source": "repeated_reject_stagnation",\n'
        '  "escalation_required": true,\n'
        '  "status": "resolved",\n'
        '  "reason": "Repeated review_classification reject",\n'
        '  "payload": { "resolution_action": "force-followup" }\n'
        '}\n',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Escalation: present (invalid)" in result.stdout
    assert "Current stage: blocked_invalid_escalation_artifact" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "Blocked reason: escalation artifact is invalid" in result.stdout
    assert "RUN STATUS: BLOCKED (invalid escalation artifact)" in result.stdout


def test_analyze_story_run_blocks_missing_resolved_decision_source(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_12-00-01")
    (run_dir / "manifest.md").write_text("- changed_files_detected: yes\n- pytest_exit_code: 0\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("MERGE RECOMMENDATION: reject\n", encoding="utf-8")
    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "resolution_action": "force-followup" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Escalation: present (invalid)" in result.stdout
    assert "Current stage: blocked_invalid_escalation_artifact" in result.stdout
    assert "RUN STATUS: BLOCKED (invalid escalation artifact)" in result.stdout


def test_analyze_story_run_blocks_wrong_resolved_decision_source(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_12-00-02")
    (run_dir / "manifest.md").write_text("- changed_files_detected: yes\n- pytest_exit_code: 0\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("MERGE RECOMMENDATION: reject\n", encoding="utf-8")
    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "decision_source": "manual_override", "resolution_action": "accept-as-is" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Escalation: present (invalid)" in result.stdout
    assert "Current stage: blocked_invalid_escalation_artifact" in result.stdout
    assert "RUN STATUS: BLOCKED (invalid escalation artifact)" in result.stdout


def test_analyze_story_run_blocks_nested_decision_source_spoof(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_12-00-03")
    (run_dir / "manifest.md").write_text("- changed_files_detected: yes\n- pytest_exit_code: 0\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("MERGE RECOMMENDATION: reject\n", encoding="utf-8")
    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "metadata": {"decision_source": "repeated_reject_stagnation"}, "resolution_action": "abort" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Escalation: present (invalid)" in result.stdout
    assert "Current stage: blocked_invalid_escalation_artifact" in result.stdout
    assert "RUN STATUS: BLOCKED (invalid escalation artifact)" in result.stdout


def test_analyze_story_run_blocks_duplicate_decision_source_keys(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_12-00-04")
    (run_dir / "manifest.md").write_text("- changed_files_detected: yes\n- pytest_exit_code: 0\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("MERGE RECOMMENDATION: reject\n", encoding="utf-8")
    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )
    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "decision_source": "repeated_reject_stagnation", "decision_source": "manual_override", "resolution_action": "force-followup" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Escalation: present (invalid)" in result.stdout
    assert "Current stage: blocked_invalid_escalation_artifact" in result.stdout
    assert "RUN STATUS: BLOCKED (invalid escalation artifact)" in result.stdout


def test_analyze_story_run_blocks_resume_when_evidence_is_stale(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    stale_head = "f" * 40

    run_dir = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_23-10-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        "- branch: feature/us-auto-19\n"
        f"- starting_head: {stale_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "automation/scripts/analyze_story_run.sh\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/x b/x\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Current stage: blocked_stale_run_evidence" in result.stdout
    assert "Latest valid stage: none" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "Blocked reason: manifest HEAD" in result.stdout
    assert current_head in result.stdout


def test_analyze_story_run_reports_accept_as_is_as_terminal_blocked(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_00-00-00")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )

    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )

    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )

    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "decision_source": "repeated_reject_stagnation", "resolution_action": "accept-as-is" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Current stage: escalation_accepted_as_is" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "RUN STATUS: BLOCKED (escalation resolved: accept-as-is)" in result.stdout


def test_analyze_story_run_reports_abort_as_terminal_blocked(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    root_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=root_dir, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root_dir, check=True)

    tracked = root_dir / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    (root_dir / ".gitignore").write_text("automation/\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", ".gitignore"], cwd=root_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root_dir, check=True, capture_output=True, text=True)

    starting_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    run_dir = make_run_dir(root_dir, "US-AUTO-28", "2026-03-24_00-00-01")

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {starting_head}\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n",
        encoding="utf-8",
    )

    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: reject\n",
        encoding="utf-8",
    )

    (run_dir / "review_gate_result.json").write_text(
        '{ "decision": "reject", "status": "failed", "decision_source": "review_classification" }',
        encoding="utf-8",
    )

    (run_dir / "escalation_result.json").write_text(
        '{ "escalation_required": true, "status": "resolved", "decision_source": "repeated_reject_stagnation", "resolution_action": "abort" }',
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-28", run_dir=run_dir)

    assert result.returncode == 0
    assert "Current stage: escalation_aborted" in result.stdout
    assert "Resume safety: blocked" in result.stdout
    assert "Next recommended command: none" in result.stdout
    assert "RUN STATUS: BLOCKED (escalation resolved: abort)" in result.stdout
