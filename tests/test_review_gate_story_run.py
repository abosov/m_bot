from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "review_gate_story_run.sh"
)


def run_review_gate(root_dir: Path, story_id: str, env: dict | None = None):
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


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


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
        f"- starting_head: {manifest_head}\n\n"
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
        "!/automation/runs/.gitkeep\n"
        "/docs/90_codex/REVIEW_CLASSIFICATION_RULES.md\n",
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
    (run_dir / "chatgpt_review_prompt.md").write_text(
        "chatgpt_review_prompt.md\n",
        encoding="utf-8",
    )
    (run_dir / "diff.patch").write_text(diff_patch, encoding="utf-8")
    (run_dir / "changed_files.txt").write_text(
        ("\n".join(changed_files) + ("\n" if changed_files else "")),
        encoding="utf-8",
    )
    (run_dir / "pytest.txt").write_text("pytest.txt\n", encoding="utf-8")


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


def test_review_gate_story_run_writes_gate_result_and_rejects(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md")

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Final decision: reject" in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert f'"reviewed_head": "{current_head(root_dir)}"' in gate_result
    assert f'"checkout_head": "{current_head(root_dir)}"' in gate_result
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result
    ledger_text = (
        root_dir / "automation" / "story_change_ledger.jsonl"
    ).read_text(encoding="utf-8")
    assert '"event":"review_outcome"' in ledger_text
    assert '"event":"story_rejected"' in ledger_text
    assert '"outcome":"reject"' in ledger_text
    assert not (run_dir / "escalation_result.json").exists()


def test_review_gate_story_run_marks_escalation_required_for_repeated_identical_rejects(
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md")

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    first_result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env={**env, "AUTOMATION_RUN_DIR": str(older_run_dir)},
    )
    assert first_result.returncode != 0
    assert not (older_run_dir / "escalation_result.json").exists()

    second_result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env={**env, "AUTOMATION_RUN_DIR": str(latest_run_dir)},
    )

    assert second_result.returncode != 0
    assert "Escalation required:" in second_result.stdout
    escalation_result = (latest_run_dir / "escalation_result.json").read_text(encoding="utf-8")
    assert '"status": "pending"' in escalation_result
    assert '"decision_source": "repeated_reject_stagnation"' in escalation_result
    assert '"previous_reject_run_id": "2026-03-14_18-56-09"' in escalation_result


def test_review_gate_story_run_passes_on_approve(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: approve' >> "$output"
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md")

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout
    assert (
        f"Run analysis command: AUTOMATION_RUN_DIR={run_dir} "
        "automation/scripts/analyze_story_run.sh US-AUTO-16"
    ) in result.stdout

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert f'"reviewed_head": "{current_head(root_dir)}"' in gate_result
    assert f'"checkout_head": "{current_head(root_dir)}"' in gate_result
    assert '"decision": "approve"' in gate_result
    assert '"status": "passed"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result
    manifest_text = (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "- ai_review_result.md" in manifest_text
    assert "- review_classification.md" in manifest_text
    assert "- review_gate_result.json" in manifest_text
    ledger_text = (
        root_dir / "automation" / "story_change_ledger.jsonl"
    ).read_text(encoding="utf-8")
    assert '"event":"review_outcome"' in ledger_text
    assert '"outcome":"approve"' in ledger_text
    assert '"event":"story_rejected"' not in ledger_text


def test_review_gate_story_run_rejects_when_decision_cannot_be_derived(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'merge recommendation pending' >> "$output"
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md")

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "gate rejected" in result.stderr

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"status": "failed"' in gate_result
    assert '"decision_source": "invalid_or_missing_merge_recommendation"' in gate_result
    assert (
        '"reason": "Review classification artifact did not contain a valid merge recommendation"'
        in gate_result
    )


def test_review_gate_story_run_rejects_when_classification_fails_before_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  exit 7
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(
        root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    )

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "gate rejected" in result.stderr

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_classification_failed"' in gate_result
    assert '"reason": "Review classification step failed"' in gate_result

    manifest_text = (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "- ai_review_result.md" in manifest_text
    assert "- review_gate_result.json" in manifest_text
    assert "- review_classification.md" not in manifest_text


def test_review_gate_story_run_rejects_when_ai_review_fails(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

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
if [[ "$output" == *"ai_review_result.md" ]]; then
  exit 9
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(
        root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    )

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "AI review step failed" in result.stderr

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "ai_review_failed"' in gate_result
    assert '"reason": "AI review step failed"' in gate_result

    manifest_text = (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "- ai_review_result.md" not in manifest_text
    assert "- review_classification.md" not in manifest_text
    assert "- review_gate_result.json" in manifest_text


def test_review_gate_story_run_blocks_before_ai_review_when_working_tree_is_dirty(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-21", "2026-03-14_18-56-10")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-21")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    ai_invocation_marker = tmp_path / "ai_invoked.txt"

    write_executable(
        fake_bin_dir / "codex",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' 'invoked' > "{ai_invocation_marker}"
cat >/dev/null
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    (root_dir / "README.md").write_text("dirty change\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "review gate blocked for 'US-AUTO-21'" in result.stderr
    assert "would not match committed state" in result.stderr
    assert "run_story.sh US-AUTO-21" in result.stderr
    assert f"AUTOMATION_RUN_DIR={run_dir}" in result.stderr
    assert "analyze_story_run.sh US-AUTO-21" in result.stderr
    assert "review_gate_story_run.sh US-AUTO-21" in result.stderr
    assert not ai_invocation_marker.exists()
    assert not (run_dir / "review_gate_result.json").exists()


def test_review_gate_story_run_ignores_ephemeral_ledger_dirty_state(
    tmp_path: Path,
) -> None:
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

    fake_bin_dir = tmp_path / "bin_ephemeral_ledger"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: approve' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-21"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout
    assert "review gate blocked" not in result.stderr


def test_review_gate_story_run_rejects_stale_changed_files_before_ai_review(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")
    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "changed_files.txt").write_text("README.md\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_stale_changed"
    fake_bin_dir.mkdir()
    ai_invocation_marker = tmp_path / "ai_invoked_stale_changed.txt"
    write_executable(
        fake_bin_dir / "codex",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' 'invoked' > "{ai_invocation_marker}"
cat >/dev/null
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Final decision: reject" in result.stdout
    assert "changed_files.txt is stale or inconsistent" in result.stderr
    assert not ai_invocation_marker.exists()
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_changed_files_mismatch"' in gate_result


def test_review_gate_story_run_rejects_stale_diff_patch_before_ai_review(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11")
    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")
    (run_dir / "diff.patch").write_text("stale diff\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_stale_diff"
    fake_bin_dir.mkdir()
    ai_invocation_marker = tmp_path / "ai_invoked_stale_diff.txt"
    write_executable(
        fake_bin_dir / "codex",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' 'invoked' > "{ai_invocation_marker}"
cat >/dev/null
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "Final decision: reject" in result.stdout
    assert "diff.patch is stale or inconsistent" in result.stderr
    assert not ai_invocation_marker.exists()
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_diff_patch_mismatch"' in gate_result


def test_review_gate_story_run_rejects_conflicting_exact_recommendations(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

    fake_bin_dir = tmp_path / "bin_conflict"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: approve' >> "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(
        root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    )

    rules_file = Path(env["CLASSIFICATION_RULES_FILE"])
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "invalid_or_missing_merge_recommendation"' in gate_result


def test_review_gate_story_run_accepts_relative_run_dir_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-12")

    write_required_review_artifacts(run_dir, root_dir)
    write_manifest(run_dir, root_dir, "US-AUTO-16")

    fake_bin_dir = tmp_path / "bin_relative"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: approve' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = os.path.relpath(run_dir, root_dir)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert "Final decision: approve" in result.stdout
    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert f'"run_dir": "{run_dir}"' in gate_result


def test_review_gate_story_run_rejects_stale_run_evidence_and_accepts_fresh_run(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    stale_run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13")
    fresh_run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-14")

    for run_dir in [stale_run_dir, fresh_run_dir]:
        write_required_review_artifacts(run_dir, root_dir)

    write_manifest(stale_run_dir, root_dir, "US-AUTO-16", starting_head="f" * 40)
    write_manifest(fresh_run_dir, root_dir, "US-AUTO-16")

    fake_bin_dir = tmp_path / "bin_head_contract"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: approve' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    stale_result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env={**env, "AUTOMATION_RUN_DIR": str(stale_run_dir)},
    )

    assert stale_result.returncode != 0
    assert "does not match current checkout HEAD" in stale_result.stderr
    stale_gate_result = (stale_run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "reject"' in stale_gate_result
    assert '"decision_source": "review_head_mismatch"' in stale_gate_result
    assert '"reviewed_head": "ffffffffffffffffffffffffffffffffffffffff"' in stale_gate_result
    assert f'"checkout_head": "{current_head(root_dir)}"' in stale_gate_result
    (root_dir / "automation" / "story_change_ledger.jsonl").unlink()

    fresh_result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env={**env, "AUTOMATION_RUN_DIR": str(fresh_run_dir)},
    )

    assert fresh_result.returncode == 0, fresh_result.stderr
    assert "Final decision: approve" in fresh_result.stdout
    fresh_gate_result = (fresh_run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in fresh_gate_result
    assert '"decision_source": "review_classification"' in fresh_gate_result
    assert f'"reviewed_head": "{current_head(root_dir)}"' in fresh_gate_result
    assert f'"checkout_head": "{current_head(root_dir)}"' in fresh_gate_result


def test_review_gate_story_run_rejects_manifest_story_id_mismatch_for_run_override(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13")

    write_required_review_artifacts(run_dir, root_dir)
    (run_dir / "manifest.md").write_text(
        "# Manifest\n- story_id: US-AUTO-999\n",
        encoding="utf-8",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "AUTOMATION_RUN_DIR manifest story_id 'US-AUTO-999'" in result.stderr


def test_review_gate_pinned_run_ignores_newer_runs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    older_run = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-09")
    pinned_run = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")
    newer_run = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11")

    for run_dir in [older_run, pinned_run, newer_run]:
        write_required_review_artifacts(run_dir, root_dir)
        write_manifest(run_dir, root_dir, "US-AUTO-16")

    # older run — reject
    (older_run / "review_gate_result.json").write_text(
        '{ "decision": "reject", "decision_source": "review_classification" }',
        encoding="utf-8",
    )

    # newer run — тоже reject (но должен игнорироваться!)
    (newer_run / "review_gate_result.json").write_text(
        '{ "decision": "reject", "decision_source": "review_classification" }',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(pinned_run)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-16"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    # ключевая проверка:
    # escalation НЕ должен считаться на основе newer_run
    assert '"status": "pending"' not in (pinned_run / "escalation_result.json").read_text(encoding="utf-8") if (pinned_run / "escalation_result.json").exists() else True
def test_prior_gate_result_malformed_json_ignored(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    older_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-09")
    latest_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-10")

    for run_dir in [older_run, latest_run]:
        write_required_review_artifacts(run_dir, root_dir)
        write_manifest(run_dir, root_dir, "US-AUTO-28")

    (older_run / "review_gate_result.json").write_text("{invalid json", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_malformed"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(latest_run)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "Escalation required:" not in result.stdout
    assert not (latest_run / "escalation_result.json").exists()


def test_prior_gate_result_duplicate_keys_ignored(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    older_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-09")
    latest_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-10")

    for run_dir in [older_run, latest_run]:
        write_required_review_artifacts(run_dir, root_dir)
        write_manifest(run_dir, root_dir, "US-AUTO-28")

    (older_run / "review_gate_result.json").write_text(
        '{"decision":"approve","decision":"reject","decision_source":"review_classification"}',
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_dupes"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(latest_run)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "Escalation required:" not in result.stdout
    assert not (latest_run / "escalation_result.json").exists()


def test_prior_gate_result_nested_spoofing_ignored(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    older_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-09")
    latest_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-10")

    for run_dir in [older_run, latest_run]:
        write_required_review_artifacts(run_dir, root_dir)
        write_manifest(run_dir, root_dir, "US-AUTO-28")

    (older_run / "review_gate_result.json").write_text(
        '{"nested":{"decision":"reject","decision_source":"review_classification"}}',
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_nested"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(latest_run)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "Escalation required:" not in result.stdout
    assert not (latest_run / "escalation_result.json").exists()


def test_prior_gate_result_wrong_source_ignored(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)

    older_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-09")
    latest_run = make_run_dir(root_dir, "US-AUTO-28", "2026-03-14_18-56-10")

    for run_dir in [older_run, latest_run]:
        write_required_review_artifacts(run_dir, root_dir)
        write_manifest(run_dir, root_dir, "US-AUTO-28")

    (older_run / "review_gate_result.json").write_text(
        '{"decision":"reject","decision_source":"other"}',
        encoding="utf-8",
    )

    fake_bin_dir = tmp_path / "bin_wrong_source"
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
if [[ "$output" == *"ai_review_result.md" ]]; then
  printf '%s\n' '# AI Review Result' > "$output"
elif [[ "$output" == *"review_classification.md" ]]; then
  printf '%s\n' '# Review Classification' > "$output"
  printf '%s\n' 'MERGE RECOMMENDATION: reject' >> "$output"
else
  : > "$output"
fi
""",
    )

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(latest_run)
    env["CODEX_BIN"] = str(fake_bin_dir / "codex")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-28"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode != 0
    assert "Escalation required:" not in result.stdout
    assert not (latest_run / "escalation_result.json").exists()
