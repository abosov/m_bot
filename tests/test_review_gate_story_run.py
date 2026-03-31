import json
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

def add_commit(root_dir: Path, relative_path: str, content: str, message: str) -> str:
    file_path = root_dir / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", relative_path], check=True, cwd=root_dir)
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=root_dir, capture_output=True, text=True)
    return current_head(root_dir)

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


def test_review_gate_story_run_accepts_committed_match_for_precommit_new_file_diff(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-16"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-14_18-56-15-precommit-new-file")

    review_artifact_base = current_head(root_dir)
    new_file = root_dir / "new_impl.txt"
    new_file.write_text("new implementation\n", encoding="utf-8")
    precommit_diff_patch = subprocess.run(
        ["git", "diff", "--no-index", "/dev/null", "new_impl.txt"],
        check=False,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout
    assert precommit_diff_patch

    subprocess.run(["git", "add", "new_impl.txt"], check=True, cwd=root_dir)
    subprocess.run(
        ["git", "commit", "-m", "add new implementation file"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(precommit_diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("new_impl.txt\n", encoding="utf-8")
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_accepts_committed_match_for_mixed_tracked_and_new_file_diff(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-16"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-14_18-56-15-mixed-diff")

    add_commit(root_dir, "z_impl.txt", "baseline tracked file\n", "add tracked impl file")
    review_artifact_base = current_head(root_dir)
    (root_dir / "z_impl.txt").write_text("baseline tracked file\nupdated implementation\n", encoding="utf-8")
    (root_dir / "new_impl.txt").write_text("new implementation\n", encoding="utf-8")
    subprocess.run(["git", "add", "z_impl.txt", "new_impl.txt"], check=True, cwd=root_dir)
    subprocess.run(
        ["git", "commit", "-m", "mixed implementation delta"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    committed_diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout
    assert committed_diff_patch.index("diff --git a/z_impl.txt b/z_impl.txt") > committed_diff_patch.index(
        "diff --git a/new_impl.txt b/new_impl.txt"
    )

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(committed_diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text("new_impl.txt\nz_impl.txt\n", encoding="utf-8")
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_ignores_committed_story_artifacts_in_fidelity_check(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    subprocess.run(
        ["git", "branch", "-M", "main"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "feat/us-auto-50-run"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    story_id = "US-AUTO-50"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-28_20-27-28")

    (root_dir / "automation" / "bundle_packs").mkdir(parents=True, exist_ok=True)
    (root_dir / "automation" / "bundles" / "active" / story_id).mkdir(parents=True, exist_ok=True)

    (root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md").write_text(
        "# bundle\n", encoding="utf-8"
    )
    (root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md").write_text(
        "# scope\n", encoding="utf-8"
    )
    (root_dir / "automation" / "bundles" / "active" / story_id / "03_master_prompt.md").write_text(
        "# prompt\n", encoding="utf-8"
    )
    (root_dir / "automation" / "scripts").mkdir(parents=True, exist_ok=True)
    (root_dir / "automation" / "scripts" / "run_story.sh").write_text(
        "#!/usr/bin/env bash\n", encoding="utf-8"
    )
    (root_dir / "automation" / "run_codex_task.sh").write_text(
        "#!/usr/bin/env bash\n", encoding="utf-8"
    )
    (root_dir / "tests").mkdir(parents=True, exist_ok=True)
    (root_dir / "tests" / "test_run_story.py").write_text(
        "def test_placeholder():\n    assert True\n", encoding="utf-8"
    )

    subprocess.run(
        [
            "git",
            "add",
            "automation/bundle_packs",
            "automation/bundles/active",
            "automation/scripts/run_story.sh",
            "automation/run_codex_task.sh",
            "tests/test_run_story.py",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "story changes"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    review_artifact_base = subprocess.run(
        ["git", "rev-parse", "HEAD^"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout.strip()

    write_required_review_artifacts(
        run_dir,
        root_dir,
        review_artifact_base=review_artifact_base,
    )

    # 🔥 ДОБАВИТЬ СРАЗУ ПОСЛЕ ЭТОГО:

    diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    filtered_diff = subprocess.run(
        ["bash", "-c", f'printf "%s" "{diff_patch}"'],
        capture_output=True,
        text=True,
    ).stdout

    # ⚠️ вручную применяем тот же ignore, что в gate
    filtered_lines = []
    skip = False

    for line in diff_patch.splitlines():
        if line.startswith("diff --git"):
            path = line.split(" a/")[1].split(" b/")[0]
            if path.startswith(f"automation/bundle_packs/{story_id}.bundle.md") or \
            path.startswith(f"automation/bundles/active/{story_id}"):
                skip = True
                continue
            else:
                skip = False

        if skip:
            continue

        filtered_lines.append(line)

    (run_dir / "diff.patch").write_text("\n".join(filtered_lines) + "\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    implementation_only = [
        "automation/run_codex_task.sh",
        "automation/scripts/run_story.sh",
        "tests/test_run_story.py",
    ]
    (run_dir / "changed_files.txt").write_text(
        "\n".join(implementation_only) + "\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_accepts_committed_rerun_diff_with_prefix_adjacent_story_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-28-F1"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-31_12-00-00-prefix-adjacent")

    review_artifact_base = current_head(root_dir)
    adjacent_story_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-28-F10" / "02_file_scope.md"
    adjacent_story_file.parent.mkdir(parents=True, exist_ok=True)
    adjacent_story_file.write_text("# sibling story scope\n", encoding="utf-8")
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("def run_story_loop():\n    return 'ok'\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "automation/bundles/active/US-AUTO-28-F10/02_file_scope.md", "services/story_loop.py"],
        check=True,
        cwd=root_dir,
    )
    subprocess.run(
        ["git", "commit", "-m", "committed rerun delta with adjacent story artifact"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    committed_diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(committed_diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text(
        "automation/bundles/active/US-AUTO-28-F10/02_file_scope.md\nservices/story_loop.py\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_rejects_true_diff_mismatch_for_prefix_adjacent_story_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-28-F1"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-31_12-00-01-prefix-adjacent-mismatch")

    review_artifact_base = current_head(root_dir)
    adjacent_story_file = root_dir / "automation" / "bundles" / "active" / "US-AUTO-28-F10" / "02_file_scope.md"
    adjacent_story_file.parent.mkdir(parents=True, exist_ok=True)
    adjacent_story_file.write_text("# sibling story scope\n", encoding="utf-8")
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("def run_story_loop():\n    return 'ok'\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "automation/bundles/active/US-AUTO-28-F10/02_file_scope.md", "services/story_loop.py"],
        check=True,
        cwd=root_dir,
    )
    subprocess.run(
        ["git", "commit", "-m", "committed rerun delta with adjacent story artifact"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    committed_diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(committed_diff_patch + "\nstale tail\n", encoding="utf-8")
    (run_dir / "changed_files.txt").write_text(
        "automation/bundles/active/US-AUTO-28-F10/02_file_scope.md\nservices/story_loop.py\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "diff.patch is stale or inconsistent" in result.stderr

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_diff_patch_mismatch"' in gate_result


def test_review_gate_story_run_accepts_committed_rerun_diff_with_same_story_bundle_artifacts(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-28-F1"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-31_12-00-02-same-story-artifact")

    review_artifact_base = current_head(root_dir)
    bundle_file = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    bundle_file.write_text("# committed bundle artifact\n", encoding="utf-8")
    active_story_file = root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md"
    active_story_file.parent.mkdir(parents=True, exist_ok=True)
    active_story_file.write_text("# committed active story scope\n", encoding="utf-8")
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("def run_story_loop():\n    return 'ok'\n", encoding="utf-8")
    subprocess.run(
        [
            "git",
            "add",
            f"automation/bundle_packs/{story_id}.bundle.md",
            f"automation/bundles/active/{story_id}/02_file_scope.md",
            "services/story_loop.py",
        ],
        check=True,
        cwd=root_dir,
    )
    subprocess.run(
        ["git", "commit", "-m", "committed rerun delta with same-story artifacts"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    committed_diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(committed_diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text(
        "\n".join(
            [
                f"automation/bundle_packs/{story_id}.bundle.md",
                f"automation/bundles/active/{story_id}/02_file_scope.md",
                "services/story_loop.py",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_rejects_true_diff_mismatch_with_same_story_bundle_artifacts(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    story_id = "US-AUTO-28-F1"
    run_dir = make_run_dir(root_dir, story_id, "2026-03-31_12-00-03-same-story-artifact-mismatch")

    review_artifact_base = current_head(root_dir)
    bundle_file = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    bundle_file.write_text("# committed bundle artifact\n", encoding="utf-8")
    active_story_file = root_dir / "automation" / "bundles" / "active" / story_id / "02_file_scope.md"
    active_story_file.parent.mkdir(parents=True, exist_ok=True)
    active_story_file.write_text("# committed active story scope\n", encoding="utf-8")
    impl_file = root_dir / "services" / "story_loop.py"
    impl_file.parent.mkdir(parents=True, exist_ok=True)
    impl_file.write_text("def run_story_loop():\n    return 'ok'\n", encoding="utf-8")
    subprocess.run(
        [
            "git",
            "add",
            f"automation/bundle_packs/{story_id}.bundle.md",
            f"automation/bundles/active/{story_id}/02_file_scope.md",
            "services/story_loop.py",
        ],
        check=True,
        cwd=root_dir,
    )
    subprocess.run(
        ["git", "commit", "-m", "committed rerun delta with same-story artifacts"],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )

    committed_diff_patch = subprocess.run(
        [
            "git",
            "diff",
            review_artifact_base,
            "--",
            ".",
            ":(exclude)automation/story_change_ledger.jsonl",
        ],
        check=True,
        cwd=root_dir,
        capture_output=True,
        text=True,
    ).stdout

    (run_dir / "review_bundle.md").write_text("review_bundle.md\n", encoding="utf-8")
    (run_dir / "chatgpt_review_prompt.md").write_text("chatgpt_review_prompt.md\n", encoding="utf-8")
    (run_dir / "diff.patch").write_text(
        committed_diff_patch.replace("return 'ok'", "return 'stale'"),
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "\n".join(
            [
                f"automation/bundle_packs/{story_id}.bundle.md",
                f"automation/bundles/active/{story_id}/02_file_scope.md",
                "services/story_loop.py",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")
    write_manifest(
        run_dir,
        root_dir,
        story_id,
        review_artifact_base=review_artifact_base,
    )
    write_pinned_review_artifacts(run_dir, recommendation="approve")

    result = run_review_gate(root_dir, story_id, env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "diff.patch is stale or inconsistent" in result.stderr

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_diff_patch_mismatch"' in gate_result


def test_review_gate_allows_exact_manual_finish_continuation(tmp_path: Path) -> None:
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

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "story_impl.txt", "second\n", "second head")

    previous_run = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_10-00-00")
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text(
        "manual_finish.txt\n",
        encoding="utf-8",
    )
    (previous_run / "diff.patch").write_text(
        "placeholder previous diff\n",
        encoding="utf-8",
    )

    run_dir = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text("", encoding="utf-8")

    exact_manual_finish_head = add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")

    # Match the current committed HEAD diff/fidelity contract for the pinned run.
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
    diff_patch = subprocess.run(
        ["git", "diff", "HEAD~1"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (run_dir / "diff.patch").write_text(diff_patch, encoding="utf-8")

    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(
        "Prompt content that does not match the AI review artifact.\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-47", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout

    gate_result = json.loads((run_dir / "review_gate_result.json").read_text(encoding="utf-8"))
    assert gate_result["decision"] == "approve"
    assert gate_result["status"] == "passed"
    assert gate_result["reviewed_head"] == exact_manual_finish_head
    assert gate_result["checkout_head"] == exact_manual_finish_head
    assert gate_result["manifest_reviewed_head"] == reviewed_head
    assert gate_result["review_head_mode"] == "manual_finish_continuation"
    assert gate_result["decision_source"] == "review_classification"


def test_review_gate_rejects_descendant_after_manual_finish_continuation(tmp_path: Path) -> None:
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

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "story_impl.txt", "second\n", "second head")

    previous_run = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_10-00-00")
    (previous_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~2\n",
        encoding="utf-8",
    )
    (previous_run / "changed_files.txt").write_text(
        "followup.txt\nmanual_finish.txt\n",
        encoding="utf-8",
    )
    (previous_run / "diff.patch").write_text("placeholder previous diff\n", encoding="utf-8")

    run_dir = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~2\n",
        encoding="utf-8",
    )
    (run_dir / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text("", encoding="utf-8")

    _manual_finish_head = add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")
    descendant_head = add_commit(root_dir, "followup.txt", "descendant\n", "descendant after manual finish")

    changed_files = sorted(
        subprocess.run(
            ["git", "diff", "--name-only", "HEAD~2"],
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
    diff_patch = subprocess.run(
        ["git", "diff", "HEAD~2"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (run_dir / "diff.patch").write_text(diff_patch, encoding="utf-8")

    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(
        "Prompt content that does not match the AI review artifact.\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-47", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "review gate rejected merge for 'US-AUTO-47'" in result.stderr
    assert "Reviewed HEAD" in result.stderr
    assert "does not match current checkout HEAD" in result.stderr

    gate_result = json.loads((run_dir / "review_gate_result.json").read_text(encoding="utf-8"))
    assert gate_result["decision"] == "reject"
    assert gate_result["status"] == "failed"
    assert gate_result["reviewed_head"] == reviewed_head
    assert gate_result["checkout_head"] == descendant_head
    assert gate_result["manifest_reviewed_head"] == reviewed_head
    assert gate_result["review_head_mode"] == "pinned_run_manifest"
    assert gate_result["decision_source"] == "review_head_mismatch"


def test_review_gate_rejects_ancestor_run_based_manual_finish_continuation(tmp_path: Path) -> None:
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

    first_head = current_head(root_dir)
    reviewed_head = add_commit(root_dir, "story_impl.txt", "second\n", "second head")

    ancestor_matching_run = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_09-00-00")
    (ancestor_matching_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )
    (ancestor_matching_run / "changed_files.txt").write_text(
        "tests/test_story_loop.py\n"
        "services/story_loop.py\n",
        encoding="utf-8",
    )
    (ancestor_matching_run / "diff.patch").write_text("placeholder older matching diff\n", encoding="utf-8")

    immediate_previous_non_matching_run = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_10-00-00")
    (immediate_previous_non_matching_run / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {first_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )
    (immediate_previous_non_matching_run / "changed_files.txt").write_text(
        "services/other_story_file.py\n",
        encoding="utf-8",
    )
    (immediate_previous_non_matching_run / "diff.patch").write_text("placeholder immediate previous diff\n", encoding="utf-8")

    run_dir = make_run_dir(root_dir, "US-AUTO-47", "2026-03-27_11-00-00")
    (run_dir / "manifest.md").write_text(
        "# Codex Run Manifest\n\n"
        f"- starting_head: {reviewed_head}\n"
        "- codex_exit_code: 0\n"
        "- materialization_status: applied\n"
        "- pytest_exit_code: 0\n"
        "- changed_files_detected: yes\n"
        "- review_artifact_base: HEAD~1\n",
        encoding="utf-8",
    )

    manual_finish_head = add_commit(root_dir, "manual_finish.txt", "manual finish\n", "manual finish")

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
    diff_patch = subprocess.run(
        ["git", "diff", "HEAD~1"],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    (run_dir / "diff.patch").write_text(diff_patch, encoding="utf-8")

    (run_dir / "ai_review_result.md").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "ai_review_raw_output.txt").write_text(
        "# AI Review\n\nLooks good.\n\n# AI Review Result\n\nApproved.\n",
        encoding="utf-8",
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(
        "Prompt content that does not match the AI review artifact.\n",
        encoding="utf-8",
    )
    (run_dir / "review_classification.md").write_text(
        "# Review Classification\n\nMERGE RECOMMENDATION: approve\n",
        encoding="utf-8",
    )

    result = run_review_gate(root_dir, "US-AUTO-47", env={"AUTOMATION_RUN_DIR": str(run_dir)})

    assert result.returncode != 0
    assert "review gate rejected merge for 'US-AUTO-47'" in result.stderr
    assert "Reviewed HEAD" in result.stderr
    assert "does not match current checkout HEAD" in result.stderr

    gate_result = json.loads((run_dir / "review_gate_result.json").read_text(encoding="utf-8"))
    assert gate_result["decision"] == "reject"
    assert gate_result["status"] == "failed"
    assert gate_result["reviewed_head"] == reviewed_head
    assert gate_result["checkout_head"] == manual_finish_head
    assert gate_result["manifest_reviewed_head"] == reviewed_head
    assert gate_result["review_head_mode"] == "pinned_run_manifest"
    assert gate_result["decision_source"] == "review_head_mismatch"
