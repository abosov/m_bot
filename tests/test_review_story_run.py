# file: tests/test_review_story_run.py
import hashlib
import json
from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "review_story_run.sh"
)


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def setup_git_repo(root_dir: Path) -> None:
    root_dir.mkdir(parents=True)
    subprocess.run(["git", "init"], check=True, cwd=root_dir, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex Test"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    (root_dir / ".gitignore").write_text(
        "/automation/runs/*\n!/automation/runs/.gitkeep\n",
        encoding="utf-8",
    )
    (root_dir / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "README.md"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

def current_head(root_dir: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_semantic_projection(
    run_dir: Path,
    *,
    story_id: str,
    review_artifact_base: str,
    source_of_truth_head: str,
) -> None:
    payload = {
        "schema_version": 1,
        "projection_kind": "semantic_companion_filter",
        "projection_source": "run_stage",
        "story_id": story_id,
        "review_artifact_base": review_artifact_base,
        "source_of_truth_head": source_of_truth_head,
        "execution_companion_filter_mode": "enabled",
        "artifacts": {
            "changed_files": {
                "path": "changed_files.txt",
                "sha256": hashlib.sha256((run_dir / "changed_files.txt").read_bytes()).hexdigest(),
            },
            "diff_patch": {
                "path": "diff.patch",
                "sha256": hashlib.sha256((run_dir / "diff.patch").read_bytes()).hexdigest(),
            },
            "review_changed_files": {
                "path": "review_changed_files.txt",
                "sha256": hashlib.sha256((run_dir / "review_changed_files.txt").read_bytes()).hexdigest(),
            },
        },
    }
    (run_dir / "semantic_projection.json").write_text(json.dumps(payload), encoding="utf-8")

def write_artifacts(run_dir: Path, *, include_manifest: bool = True) -> None:
    artifact_names = [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]
    if include_manifest:
        artifact_names.insert(0, "manifest.md")

    for artifact_name in artifact_names:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")


def test_review_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_review_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_review_story_run_reports_latest_run_with_manifest(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    older_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_10-00-00")
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(older_run_dir)
    write_artifacts(latest_run_dir)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert f"Latest run: {latest_run_dir}" in result.stdout
    assert f" - {latest_run_dir / 'manifest.md'}" in result.stdout
    assert "Review safety: SAFE" in result.stdout
    assert (
        f"Workflow helper (source of truth): AUTOMATION_RUN_DIR={latest_run_dir} "
        "automation/scripts/analyze_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        f"Deterministic gate command: AUTOMATION_RUN_DIR={latest_run_dir} "
        "automation/scripts/review_gate_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        "Use analyze_story_run.sh to determine current stage, resume safety, "
        "and next recommended command."
    ) in result.stdout
    assert "does not enforce workflow transitions" in result.stdout


def test_review_story_run_fails_when_manifest_is_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir, include_manifest=False)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "manifest.md" in result.stderr


def test_review_story_run_blocks_when_working_tree_is_dirty(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir)
    (root_dir / "README.md").write_text("dirty change\n", encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Review safety: BLOCKED" in result.stdout
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stdout
    assert "commit the changes if they belong in the reviewed diff, or discard them if they do not" in result.stdout
    assert f"AUTOMATION_RUN_DIR={latest_run_dir}" in result.stdout
    assert "analyze_story_run.sh US-AUTO-21" in result.stdout
    assert "follow the next recommended command from analyze output" in result.stdout
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stderr


def test_review_story_run_blocks_dirty_workspace_before_artifact_validation(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir, include_manifest=False)
    (root_dir / "README.md").write_text("dirty change\n", encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Review safety: BLOCKED" in result.stdout
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stdout
    assert "manifest.md" not in result.stderr
    assert "workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD" in result.stderr


def test_review_story_run_ignores_ephemeral_ledger_dirty_state(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-13_11-00-00")
    write_artifacts(latest_run_dir)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")
    subprocess.run(
        ["git", "add", "automation/story_change_ledger.jsonl"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "track ledger"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    ledger_path.write_text('{"dirty":true}\n', encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Review safety: SAFE" in result.stdout
    assert "Review safety: BLOCKED" not in result.stdout


def test_review_story_run_accepts_relative_run_dir_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    older_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_10-00-00")
    selected_run_dir = make_run_dir(root_dir, "US-AUTO-7", "2026-03-13_11-00-00")
    write_artifacts(older_run_dir)
    write_artifacts(selected_run_dir)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = os.path.relpath(selected_run_dir, root_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-7"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert f"Latest run: {selected_run_dir}" in result.stdout
    assert (
        f"Workflow helper (source of truth): AUTOMATION_RUN_DIR={selected_run_dir} "
        "automation/scripts/analyze_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        f"Deterministic gate command: AUTOMATION_RUN_DIR={selected_run_dir} "
        "automation/scripts/review_gate_story_run.sh US-AUTO-7"
    ) in result.stdout
    assert (
        "Use analyze_story_run.sh to determine current stage, resume safety, "
        "and next recommended command."
    ) in result.stdout
    assert "does not enforce workflow transitions" in result.stdout


def test_review_story_run_accepts_valid_projection_with_stale_legacy_changed_files(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-75"
    run_dir = make_run_dir(root_dir, story_id, "projection-fast-path")

    review_artifact_base = current_head(root_dir)
    (root_dir / "impl.txt").write_text("implementation\n", encoding="utf-8")
    subprocess.run(["git", "add", "impl.txt"], check=True, cwd=root_dir)
    subprocess.run(["git", "commit", "-m", "add implementation"], check=True, cwd=root_dir, capture_output=True, text=True)
    source_head = current_head(root_dir)

    write_artifacts(run_dir)
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {source_head}\n"
        f"- review_artifact_base: {review_artifact_base}\n"
        "- execution_companion_filter_mode: enabled\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text("legacy-stale.txt\n", encoding="utf-8")
    (run_dir / "review_changed_files.txt").write_text("impl.txt\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, "--", "impl.txt"],
            check=True,
            cwd=root_dir,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )
    write_semantic_projection(
        run_dir,
        story_id=story_id,
        review_artifact_base=review_artifact_base,
        source_of_truth_head=source_head,
    )

    env = os.environ.copy()
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

    assert result.returncode == 0, result.stderr
    assert "Latest run:" in result.stdout
    assert "filtered review artifacts are stale or inconsistent with recomputed baseline" not in result.stderr


def test_review_story_run_blocks_companion_filtered_stale_review_surface(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    story_id = "US-AUTO-70"
    scope_file = root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md"
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(
        "# Scope\n\n"
        "## Files Allowed To Change\n"
        "- `services/story_loop.py`\n\n"
        "## Files Not Allowed To Change\n"
        "- `backend/**`\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", str(scope_file.relative_to(root_dir))],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add code-only scope"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    review_artifact_base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout.strip()
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("implementation\n", encoding="utf-8")
    registry_file = root_dir / "docs" / "90_codex" / "epics" / "US-AUTO_REGISTRY.md"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text("registry\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "services/story_loop.py", "docs/90_codex/epics/US-AUTO_REGISTRY.md"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    reviewed_head = subprocess.run(
        ["git", "commit", "-m", "impl plus companion"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    assert reviewed_head.returncode == 0

    run_dir = make_run_dir(root_dir, story_id, "2026-04-06_12-00-00")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {subprocess.run(['git', 'rev-parse', 'HEAD'], check=True, cwd=root_dir, capture_output=True, text=True).stdout.strip()}\n"
        f"- review_artifact_base: {review_artifact_base}\n"
        "- execution_companion_filter_mode: enabled\n",
        encoding="utf-8",
    )
    write_artifacts(run_dir, include_manifest=False)
    (run_dir / "manifest.md").write_text((run_dir / "manifest.md").read_text(encoding="utf-8"), encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("services/wrong.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff --git a/services/wrong.py b/services/wrong.py\n", encoding="utf-8")

    env = os.environ.copy()
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
    assert "filtered review artifacts are stale or inconsistent with recomputed baseline" in result.stderr


def test_review_story_run_accepts_companion_filtered_review_surface_for_mixed_scope_story(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    story_id = "US-AUTO-73"
    scope_file = root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md"
    scope_file.parent.mkdir(parents=True, exist_ok=True)
    scope_file.write_text(
        "# Scope\n\n"
        "## Files Allowed To Change\n"
        "- `services/story_loop.py`\n"
        "- `docs/release_notes.md`\n\n"
        "## Files Not Allowed To Change\n"
        "- `backend/**`\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", str(scope_file.relative_to(root_dir))],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add mixed scope"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    review_artifact_base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout.strip()
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("implementation\n", encoding="utf-8")
    registry_file = root_dir / "docs" / "90_codex" / "epics" / "US-AUTO_REGISTRY.md"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text("registry\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "services/story_loop.py", "docs/90_codex/epics/US-AUTO_REGISTRY.md"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "impl plus companion"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    filtered_impl_diff = subprocess.run(
        ["git", "diff", review_artifact_base, "--", "services/story_loop.py"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    run_dir = make_run_dir(root_dir, story_id, "2026-04-06_12-05-00")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {subprocess.run(['git', 'rev-parse', 'HEAD'], check=True, cwd=root_dir, capture_output=True, text=True).stdout.strip()}\n"
        f"- review_artifact_base: {review_artifact_base}\n"
        "- execution_companion_filter_mode: enabled\n",
        encoding="utf-8",
    )
    write_artifacts(run_dir, include_manifest=False)
    (run_dir / "changed_files.txt").write_text("services/story_loop.py\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(filtered_impl_diff, encoding="utf-8")

    env = os.environ.copy()
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

    assert result.returncode == 0, result.stderr
    assert "Review safety: SAFE" in result.stdout
    assert "filtered review artifacts are stale or inconsistent with recomputed baseline" not in result.stderr

def test_review_rejects_invalid_projection(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    story_id = "US-AUTO-75"
    run_dir = make_run_dir(root_dir, story_id, "review-invalid-projection")

    review_artifact_base = current_head(root_dir)

    impl_file = root_dir / "impl.txt"
    impl_file.write_text("implementation\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "impl.txt"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add implementation"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    source_head = current_head(root_dir)

    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {source_head}\n"
        f"- review_artifact_base: {review_artifact_base}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- execution_companion_filter_mode: enabled\n",
        encoding="utf-8",
    )
    (run_dir / "review_bundle.md").write_text("# Review Bundle\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("impl.txt\n", encoding="utf-8")
    (run_dir / "pytest.txt").write_text("4 passed\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(
        subprocess.run(
            ["git", "diff", review_artifact_base, "--", "impl.txt"],
            cwd=root_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout,
        encoding="utf-8",
    )
    (run_dir / "semantic_projection.json").write_text("{invalid\n", encoding="utf-8")

    env = os.environ.copy()
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
