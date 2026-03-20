from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "review_gate_story_run.sh"
)


def make_run_dir(base_dir: Path, story_id: str, run_id: str) -> Path:
    run_dir = base_dir / "automation" / "runs" / story_id / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


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

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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
    assert '"decision": "reject"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result


def test_review_gate_story_run_passes_on_approve(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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

    gate_result = (run_dir / "review_gate_result.json").read_text(encoding="utf-8")
    assert '"decision": "approve"' in gate_result
    assert '"status": "passed"' in gate_result
    assert '"decision_source": "review_classification"' in gate_result
    manifest_text = (run_dir / "manifest.md").read_text(encoding="utf-8")
    assert "- ai_review_result.md" in manifest_text
    assert "- review_classification.md" in manifest_text
    assert "- review_gate_result.json" in manifest_text


def test_review_gate_story_run_rejects_when_decision_cannot_be_derived(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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
    assert "review_gate_story_run.sh US-AUTO-21" in result.stderr
    assert not ai_invocation_marker.exists()
    assert not (run_dir / "review_gate_result.json").exists()

def test_review_gate_story_run_rejects_conflicting_exact_recommendations(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-11")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n\n## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text(
        "# Manifest\n"
        "- story_id: US-AUTO-16\n\n"
        "## Artifacts\n- manifest.md\n",
        encoding="utf-8",
    )

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


def test_review_gate_story_run_rejects_manifest_story_id_mismatch_for_run_override(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    setup_git_repo(root_dir)
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-13")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
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
