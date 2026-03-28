from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "review_gate_story_run.sh"
)


def run_review_gate(root_dir: Path, story_id: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    env_vars = os.environ.copy()
    if env:
        env_vars.update(env)

    env_vars["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env_vars["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    return subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env_vars,
        cwd=root_dir,
    )


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def current_head(root_dir: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_manifest(
    run_dir: Path,
    root_dir: Path,
    story_id: str,
    *,
    starting_head: str | None = None,
    review_artifact_base: str | None = None,
) -> None:
    manifest_head = starting_head or current_head(root_dir)
    artifact_base = review_artifact_base or current_head(root_dir)
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        f"- story_id: {story_id}\n"
        f"- starting_head: {manifest_head}\n"
        f"- review_artifact_base: {artifact_base}\n\n"
        "## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )


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
        "/automation/runs/*\n"
        "!/automation/runs/.gitkeep\n",
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


def write_required_review_artifacts(
    run_dir: Path,
    root_dir: Path,
    *,
    review_artifact_base: str | None = None,
) -> None:
    artifact_base = review_artifact_base or current_head(root_dir)
    diff_patch = subprocess.run(
        [
            "git",
            "diff",
            artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout
    changed_files_output = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
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
        ("\n".join(changed_files) + ("\n" if changed_files else "")),
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")


def write_pinned_review_artifacts(run_dir: Path, *, recommendation: str | None = "approve") -> None:
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )
    if recommendation is None:
        (run_dir / "review_classification.md").write_text(
            "# Review Classification\n\nmerge recommendation pending\n",
            encoding="utf-8",
        )
    else:
        (run_dir / "review_classification.md").write_text(
            "# Review Classification\n\n"
            f"MERGE RECOMMENDATION: {recommendation}\n",
            encoding="utf-8",
        )


def test_review_gate_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_review_gate_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_review_gate_story_run_approves_from_pinned_artifacts_without_recompute(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"status": "passed"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result
    assert f'"reviewed_head": "{current_head(root_dir)}"' in gate_result
    assert f'"checkout_head": "{current_head(root_dir)}"' in gate_result


def test_review_gate_story_run_rejects_missing_ai_review_artifact_without_recompute(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: ai_review_missing_artifact" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "ai_review_missing_artifact"' in gate_result
    assert '"reason": "Pinned AI review artifact is missing;' in gate_result


def test_review_gate_story_run_rejects_missing_normalized_ai_review_when_raw_output_exists(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11-raw-only")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: ai_review_normalization_failed" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "ai_review_normalization_failed"' in gate_result
    assert '"reason": "Pinned normalized AI review artifact is missing while raw output exists at ' in gate_result


def test_review_gate_story_run_rejects_missing_classification_artifact_without_recompute(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-12")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: review_classification_missing_artifact" in result.stderr
    assert not (run_dir / "review_classification.md").exists()

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "review_classification_missing_artifact"' in gate_result


def test_review_gate_story_run_rejects_invalid_classification_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    write_pinned_review_artifacts(run_dir, recommendation=None)

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "invalid_or_missing_merge_recommendation"' in gate_result


def test_review_gate_story_run_rejects_invalid_ai_review_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13-invalid-ai")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "ai_review_result.md").write_text("# AI Review Result\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: ai_review_normalization_failed" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "ai_review_normalization_failed"' in gate_result


def test_review_gate_story_run_rejects_prompt_echo_ai_review_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13-echo-ai")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    prompt_text = (
        "# AI Review\n\n"
        "- Finding echoed from prompt.\n\n"
        "# AI Review Result\n\n"
        "PASS\n"
        "This is a long prompt line to trigger echo detection during gate validation.\n"
        "This is a long prompt line to trigger echo detection during gate validation.\n"
        "This is a long prompt line to trigger echo detection during gate validation.\n"
        "This is a long prompt line to trigger echo detection during gate validation.\n"
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(prompt_text, encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text(prompt_text, encoding="utf-8")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: ai_review_normalization_failed" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "ai_review_normalization_failed"' in gate_result


def test_review_gate_story_run_rejects_unreadable_ai_review_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13-unreadable-ai")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "ai_review_result.md").write_bytes(b"\xff\xfe\x00\x00")
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "decision: reject, source: ai_review_unreadable_artifact" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "ai_review_unreadable_artifact"' in gate_result


def test_review_gate_story_run_marks_escalation_required_for_repeated_identical_pinned_rejects(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    older_run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-09")
    latest_run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(older_run_dir, root_dir)
    write_required_review_artifacts(latest_run_dir, root_dir)
    write_manifest(older_run_dir, root_dir, "US-AUTO-16")
    write_manifest(latest_run_dir, root_dir, "US-AUTO-16")
    write_pinned_review_artifacts(older_run_dir, recommendation="reject")
    write_pinned_review_artifacts(latest_run_dir, recommendation="reject")

    first_result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(older_run_dir)})
    assert first_result.returncode != 0
    assert not (older_run_dir / "escalation_result.json").exists()

    second_result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(latest_run_dir)})

    assert second_result.returncode != 0
    assert "Escalation required:" in second_result.stdout
    escalation_result = (latest_run_dir / "escalation_result.json").read_text(encoding="utf-8")
    assert '"status": "pending"' in escalation_result
    assert '"decision_source": "repeated_reject_stagnation"' in escalation_result
    assert '"previous_reject_run_id": "2026-03-14_18-56-09"' in escalation_result


def test_review_gate_story_run_blocks_before_consuming_artifacts_when_working_tree_is_dirty(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-21")
    write_pinned_review_artifacts(run_dir, recommendation="approve")
    (root_dir / "README.md").write_text("dirty change\n", encoding="utf-8")

    result = run_review_gate(root_dir, "US-AUTO-21", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "review gate blocked for 'US-AUTO-21'" in result.stderr
    assert "would make gate evaluation diverge from committed HEAD and origin/main...HEAD" in result.stderr
    assert "commit the changes if they belong in the reviewed diff, or discard them if they do not" in result.stderr
    assert not (run_dir / "review_gate_result.json").exists()


def test_review_gate_story_run_ignores_ephemeral_ledger_dirty_state(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-14_18-56-10")

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

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-21")
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, "US-AUTO-21", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout


def test_review_gate_story_run_rejects_stale_changed_files_before_consuming_pinned_inputs(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-14")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    write_pinned_review_artifacts(run_dir, recommendation="approve")
    (run_dir / "changed_files.txt").write_text("README.md\n", encoding="utf-8")

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "changed_files.txt is stale or inconsistent" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "review_changed_files_mismatch"' in gate_result


def test_review_gate_story_run_rejects_stale_diff_patch_before_consuming_pinned_inputs(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-15")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    write_pinned_review_artifacts(run_dir, recommendation="approve")
    (run_dir / "diff.patch").write_text("stale diff\n", encoding="utf-8")

    result = run_review_gate(root_dir, "US-AUTO-16", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "diff.patch is stale or inconsistent" in result.stderr
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision_source": "review_diff_patch_mismatch"' in gate_result
