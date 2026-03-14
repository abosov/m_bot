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
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
        "manifest.md",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

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
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
        "manifest.md",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

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


def test_review_gate_story_run_rejects_when_decision_cannot_be_derived(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = make_run_dir(root_dir, "US-AUTO-16", "2026-03-14_18-56-10")

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
        "manifest.md",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

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
    assert '"decision_source": "review_classification_failed"' in gate_result
