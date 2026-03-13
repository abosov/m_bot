from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "classify_review_story_run.sh"
)


def test_review_classification_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_review_classification_script_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_review_classification_script_writes_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    runs_dir = root_dir / "automation" / "runs" / "US-AUTO-6" / "2026-03-13_16-16-09"
    runs_dir.mkdir(parents=True)

    ai_review_file = runs_dir / "ai_review_result.md"
    ai_review_file.write_text("# AI Review Result\n\n- Finding A\n", encoding="utf-8")

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n\nClassify findings.\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
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
printf '%s\\n' '# Review Classification' > "$output"
printf '%s\\n' '1. findings by classification' >> "$output"
printf '%s\\n' '5. merge recommendation (reject)' >> "$output"
printf '%s\\n' 'raw-classification-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-6"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "Review classification written:" in result.stdout
    assert (runs_dir / "review_classification.md").read_text(encoding="utf-8").startswith(
        "# Review Classification"
    )
    assert (
        runs_dir / "review_classification_raw_output.txt"
    ).read_text(encoding="utf-8").strip() == "raw-classification-output"


def test_review_classification_script_fails_without_ai_review(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    runs_dir = root_dir / "automation" / "runs" / "US-AUTO-6" / "2026-03-13_16-16-09"
    runs_dir.mkdir(parents=True)

    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True)
    rules_file.write_text("# Rules\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-6"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "required file not found" in result.stderr
    assert "ai_review_result.md" in result.stderr
