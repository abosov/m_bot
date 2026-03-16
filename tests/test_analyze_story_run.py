from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "analyze_story_run.sh"
)


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
    (latest_run_dir / "ai_review_result.md").write_text("# AI Review\n", encoding="utf-8")
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
    assert "Branch: feature/us-auto-19" in result.stdout
    assert (
        "Changed Files\n"
        "4 files (automation/scripts/analyze_story_run.sh, "
        "tests/test_analyze_story_run.py, docs/90_codex/STORY_EXECUTION_CHECKLIST.md, ...)"
    ) in result.stdout
    assert "Pytest\npass (exit 0" in result.stdout
    assert "Classification: present (approve)" in result.stdout
    assert "Gate: present (approve/passed via review_classification)" in result.stdout
    assert "RUN STATUS: READY FOR MERGE REVIEW (gate approve)" in result.stdout


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
    assert "Classification: present (invalid recommendation)" in result.stdout
    assert "Gate: missing" in result.stdout
    assert "RUN STATUS: CHECK REVIEW CLASSIFICATION (invalid recommendation)" in result.stdout
    assert "RUN STATUS: CHECK RUN OUTPUT (no changed files detected)" not in result.stdout

def test_analyze_story_run_accepts_split_line_recommendation_format(tmp_path: Path) -> None:
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
    (run_dir / "pytest.txt").write_text(
        "============================= test session starts ==============================\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "5. Merge recommendation\n"
        "- `approve`\n\n"
        "MERGE RECOMMENDATION\n"
        "approve\n",
        encoding="utf-8",
    )

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Classification: present (approve)" in result.stdout
    assert "Classification: present (invalid recommendation)" not in result.stdout
    assert "RUN STATUS: READY TO RUN GATE (classification approve)" in result.stdout

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
    assert "Classification: present (invalid recommendation)" in result.stdout
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
    (run_dir / "ai_review_result.md").write_text("# AI Review\n", encoding="utf-8")

    result = run_script(root_dir, "US-AUTO-19", run_dir=run_dir)

    assert result.returncode == 0, result.stderr
    assert "Pytest\nfail (exit 1; 1 failed)" in result.stdout
    assert "AI review: present" in result.stdout
    assert "RUN STATUS: BLOCKED (pytest failing)" in result.stdout
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
    assert "invalid STORY_ID" in result.stderr


def test_analyze_story_run_fails_when_story_root_is_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"

    result = run_script(root_dir, "US-AUTO-19")

    assert result.returncode != 0
    assert "story run root not found" in result.stderr

def test_analyze_story_run_rejects_parent_dir_escape_in_run_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir_19 = make_run_dir(root_dir, "US-AUTO-19", "2026-03-16_14-00-00")
    run_dir_21 = make_run_dir(root_dir, "US-AUTO-21", "2026-03-16_15-00-00")

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