from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "ai_review_story_run.sh"
)

VALID_AI_REVIEW = "# AI Review\n\n- Finding A\n\n# AI Review Result\n\nPASS\n"


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
printf '%s\\n' '# AI Review' > "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '- Finding A' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' '# AI Review Result' >> "$output"
printf '%s\\n' '' >> "$output"
printf '%s\\n' 'PASS' >> "$output"
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
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == VALID_AI_REVIEW
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


def test_ai_review_story_run_rejects_incomplete_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-10-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_incomplete"
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

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_rejects_malformed_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-15-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_malformed"
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
printf '%s\\n' 'raw text without expected heading' > "$output"
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()


def test_ai_review_story_run_rejects_unreadable_artifact(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-20-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_unreadable"
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
python3 - "$output" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_bytes(b"\\xff\\xfe\\x00\\x00")
PY
printf '%s\\n' 'raw-ai-output'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8").strip() == "raw-ai-output"


def test_ai_review_story_run_normalizes_raw_output_when_result_file_missing(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-25-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_raw_only"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding recovered from raw output'
printf '%s\\n' ''
printf '%s\\n' '# AI Review Result'
printf '%s\\n' ''
printf '%s\\n' 'PASS'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == (
        "# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )


def test_ai_review_story_run_fails_closed_when_raw_output_cannot_be_normalized(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-30-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_raw_invalid"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' 'plain text without normalized heading'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "plain text without normalized heading\n"
    )


def test_ai_review_story_run_recovers_invalid_result_from_normalizable_raw_output(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-35-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_invalid_result_recovered"
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
printf '%s\\n' 'preamble before normalized review'
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding recovered from raw output'
printf '%s\\n' ''
printf '%s\\n' '# AI Review Result'
printf '%s\\n' ''
printf '%s\\n' 'PASS'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (run_dir / "ai_review_result.md").read_text(encoding="utf-8") == (
        "# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )
    assert (run_dir / "ai_review_raw_output.txt").read_text(encoding="utf-8") == (
        "preamble before normalized review\n# AI Review\n\n- Finding recovered from raw output\n\n# AI Review Result\n\nPASS\n"
    )


def test_ai_review_story_run_rejects_prompt_echo_output(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-40-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    prompt_text = (
        "# AI Review\n\n"
        "- Finding echoed from prompt.\n\n"
        "# AI Review Result\n\n"
        "PASS\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
        "This is a long prompt line to force robust prompt-echo detection in the validator.\n"
    )
    (run_dir / "chatgpt_review_prompt.md").write_text(prompt_text, encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_echo"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
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
cat "{run_dir / 'chatgpt_review_prompt.md'}" > "$output"
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()


def test_ai_review_story_run_rejects_output_missing_required_sections(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-5" / "2026-03-20_12-45-00"
    run_dir.mkdir(parents=True)

    for artifact_name in [
        "review_bundle.md",
        "chatgpt_review_prompt.md",
        "diff.patch",
        "changed_files.txt",
        "pytest.txt",
    ]:
        (run_dir / artifact_name).write_text(f"{artifact_name}\n", encoding="utf-8")

    fake_bin_dir = tmp_path / "bin_missing_section"
    fake_bin_dir.mkdir()
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\\n' '# AI Review'
printf '%s\\n' ''
printf '%s\\n' '- Finding without required result section'
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), "US-AUTO-5"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not (run_dir / "ai_review_result.md").exists()
