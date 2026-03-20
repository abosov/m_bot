from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "ai_review_story_run.sh"
)


def test_ai_review_story_run_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_ai_review_story_run_is_valid_bash() -> None:
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_ai_review_story_run_accepts_relative_run_dir_override(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-00-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-5\n", encoding="utf-8")

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
printf '%s\\n' '# AI Review Result' > "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = os.path.relpath(run_dir, root_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=root_dir,
    )

    assert result.returncode == 0, result.stderr
    assert "AI review result written:" in result.stdout
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8").startswith("# AI Review Result")
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_rejects_manifest_story_id_mismatch_for_run_override(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-05-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-99\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "AUTOMATION_RUN_DIR manifest story_id 'US-AUTO-99'" in result.stderr
