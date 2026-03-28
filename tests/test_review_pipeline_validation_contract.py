from pathlib import Path
import os
import subprocess


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "automation"
    / "scripts"
    / "classify_review_story_run.sh"
)


def make_rules_file(root_dir: Path) -> Path:
    rules_file = root_dir / "docs" / "90_codex" / "REVIEW_CLASSIFICATION_RULES.md"
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text("# Rules\n\nClassify findings.\n", encoding="utf-8")
    return rules_file


def make_fake_codex(fake_bin_dir: Path, marker_file: Path) -> None:
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    fake_codex = fake_bin_dir / "codex"
    fake_codex.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' invoked > "{marker_file}"
exit 0
""",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)


def run_classification(
    root_dir: Path,
    story_id: str,
    *,
    run_dir: Path,
    fake_bin_dir: Path,
    rules_file: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNS_ROOT"] = str(root_dir / "automation" / "runs")
    env["AUTOMATION_RUN_DIR"] = str(run_dir)
    env["CLASSIFICATION_RULES_FILE"] = str(rules_file)

    return subprocess.run(
        ["bash", str(SCRIPT_PATH), story_id],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_classification_fail_closed_on_missing_ai_review_and_clears_stale_outputs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-43" / "2026-03-27_10-00-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-43\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = make_rules_file(root_dir)
    marker_file = tmp_path / "codex_invoked.txt"
    fake_bin_dir = tmp_path / "bin_missing"
    make_fake_codex(fake_bin_dir, marker_file)

    result = run_classification(
        root_dir,
        "US-AUTO-43",
        run_dir=run_dir,
        fake_bin_dir=fake_bin_dir,
        rules_file=rules_file,
    )

    assert result.returncode != 0
    assert "ai_review_missing_artifact" in result.stderr
    assert "review classification blocked for 'US-AUTO-43'" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classification_fail_closed_on_malformed_ai_review_and_clears_stale_outputs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-43" / "2026-03-27_10-05-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-43\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text("plain text only\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = make_rules_file(root_dir)
    marker_file = tmp_path / "codex_invoked_malformed.txt"
    fake_bin_dir = tmp_path / "bin_malformed"
    make_fake_codex(fake_bin_dir, marker_file)

    result = run_classification(
        root_dir,
        "US-AUTO-43",
        run_dir=run_dir,
        fake_bin_dir=fake_bin_dir,
        rules_file=rules_file,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classification_fail_closed_on_incomplete_ai_review_and_clears_stale_outputs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-43" / "2026-03-27_10-10-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-43\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_text("# AI Review Result\n", encoding="utf-8")
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = make_rules_file(root_dir)
    marker_file = tmp_path / "codex_invoked_incomplete.txt"
    fake_bin_dir = tmp_path / "bin_incomplete"
    make_fake_codex(fake_bin_dir, marker_file)

    result = run_classification(
        root_dir,
        "US-AUTO-43",
        run_dir=run_dir,
        fake_bin_dir=fake_bin_dir,
        rules_file=rules_file,
    )

    assert result.returncode != 0
    assert "ai_review_normalization_failed" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()


def test_classification_fail_closed_on_unreadable_ai_review_and_clears_stale_outputs(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    run_dir = root_dir / "automation" / "runs" / "US-AUTO-43" / "2026-03-27_10-15-00"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.md").write_text("- story_id: US-AUTO-43\n", encoding="utf-8")
    (run_dir / "ai_review_result.md").write_bytes(b"\xff\xfe\x00\x00")
    (run_dir / "review_classification.md").write_text("stale\n", encoding="utf-8")
    (run_dir / "review_classification_raw_output.txt").write_text("stale\n", encoding="utf-8")

    rules_file = make_rules_file(root_dir)
    marker_file = tmp_path / "codex_invoked_unreadable.txt"
    fake_bin_dir = tmp_path / "bin_unreadable"
    make_fake_codex(fake_bin_dir, marker_file)

    result = run_classification(
        root_dir,
        "US-AUTO-43",
        run_dir=run_dir,
        fake_bin_dir=fake_bin_dir,
        rules_file=rules_file,
    )

    assert result.returncode != 0
    assert "ai_review_unreadable_artifact" in result.stderr
    assert not marker_file.exists()
    assert not (run_dir / "review_classification.md").exists()
    assert not (run_dir / "review_classification_raw_output.txt").exists()
