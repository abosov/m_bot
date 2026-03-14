from pathlib import Path
import os
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
MATERIALIZE_SCRIPT = REPO_ROOT / "automation" / "scripts" / "materialize_story_bundle.sh"
VALIDATE_SCRIPT = REPO_ROOT / "automation" / "scripts" / "validate_story_bundle.sh"
RUN_STORY_SCRIPT = REPO_ROOT / "automation" / "scripts" / "run_story.sh"

REQUIRED_FILES = [
    "00_story.md",
    "01_context_bundle.md",
    "02_file_scope.md",
    "03_master_prompt.md",
    "04_review_checklist.md",
    "05_followups.md",
    "06_manual_actions.md",
]


def run_script(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def valid_bundle_files(story_id: str) -> dict[str, str]:
    return {
        "00_story.md": f"""# {story_id}: Test Story

## Story ID and Title
- Story ID: `{story_id}`
- Title: `Test Story`

## Objective
- objective

## Scope
- scope

## Non-goals
- non-goal

## Dependencies
- dependency

## Source of Truth
- source

## Current Code Reality
- reality

## Target Outcome
- target
""",
        "01_context_bundle.md": """# Context

## Source of Truth
- source

## Current Code Reality
- reality

## Architectural Intent
- architecture

## Risks
- risk

## Acceptance Notes
- acceptance
""",
        "02_file_scope.md": """# File Scope

## Files Allowed To Change
- automation/scripts/example.sh

## Files Not Allowed To Change
- backend/**
""",
        "03_master_prompt.md": """# Prompt

## Role
- role

## Goal
- goal

## Source of Truth
- source

## Files Allowed To Change
- automation/scripts/example.sh

## Files Not Allowed To Change
- backend/**

## Output
1. changed files
""",
        "04_review_checklist.md": """# Review

## Scope Validation
- [ ] in scope

## Functional Validation
- [ ] validated

## Verification
- [ ] tests
""",
        "05_followups.md": """# Followups

## Follow-Up Prompt Queue
- none

## Iteration Notes
- notes
""",
        "06_manual_actions.md": """# Manual

## Required Human Actions
- none

## Completion Status
- [x] No manual actions required
""",
    }


def write_bundle(bundle_dir: Path, story_id: str) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for name, content in valid_bundle_files(story_id).items():
        (bundle_dir / name).write_text(content, encoding="utf-8")


def write_pack(pack_path: Path, story_id: str) -> None:
    parts = [
        "# Story Bundle Pack",
        f"Story-ID: {story_id}",
        "Version: 1",
        "",
    ]
    for name, content in valid_bundle_files(story_id).items():
        parts.append(f"=== FILE: {name} ===")
        parts.append(content.rstrip())
        parts.append("")
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")


def test_bundle_materialization_creates_required_files(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    story_id = "US-AUTO-99"
    pack_path = root_dir / "automation" / "bundle_packs" / f"{story_id}.bundle.md"
    write_pack(pack_path, story_id)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    result = run_script(["bash", str(MATERIALIZE_SCRIPT), story_id], env=env)

    assert result.returncode == 0, result.stderr
    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    assert bundle_dir.is_dir()
    assert sorted(path.name for path in bundle_dir.iterdir()) == REQUIRED_FILES


def test_validate_story_bundle_fails_on_unresolved_placeholder(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    story_id = "US-AUTO-98"
    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    write_bundle(bundle_dir, story_id)

    placeholder_token = "_" + "!" + "_"
    content = (bundle_dir / "00_story.md").read_text(encoding="utf-8")
    (bundle_dir / "00_story.md").write_text(
        content + f"\n{placeholder_token}\n", encoding="utf-8"
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    result = run_script(["bash", str(VALIDATE_SCRIPT), story_id], env=env)

    assert result.returncode != 0
    assert "unresolved canonical placeholder" in result.stderr


def test_validate_story_bundle_fails_on_legacy_unresolved_token(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    story_id = "US-AUTO-95"
    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    write_bundle(bundle_dir, story_id)

    content = (bundle_dir / "01_context_bundle.md").read_text(encoding="utf-8")
    (bundle_dir / "01_context_bundle.md").write_text(
        content + "\n<UNRESOLVED>\n", encoding="utf-8"
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    result = run_script(["bash", str(VALIDATE_SCRIPT), story_id], env=env)

    assert result.returncode != 0
    assert "unresolved <UNRESOLVED> placeholders" in result.stderr


def test_validate_story_bundle_fails_on_missing_required_sections(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    story_id = "US-AUTO-97"
    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    write_bundle(bundle_dir, story_id)

    (bundle_dir / "03_master_prompt.md").write_text(
        """# Prompt

## Role
- role

## Source of Truth
- source

## Files Allowed To Change
- automation/scripts/example.sh

## Files Not Allowed To Change
- backend/**

## Output
1. changed files
""",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)

    result = run_script(["bash", str(VALIDATE_SCRIPT), story_id], env=env)

    assert result.returncode != 0
    assert "missing required section" in result.stderr
    assert "## Goal" in result.stderr


def test_run_story_refuses_invalid_bundle(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    story_id = "US-AUTO-96"
    bundle_dir = root_dir / "automation" / "bundles" / "active" / story_id
    write_bundle(bundle_dir, story_id)

    placeholder_token = "_" + "!" + "_"
    (bundle_dir / "01_context_bundle.md").write_text(
        f"# Context\n\n## Source of Truth\n- source\n\n## Current Code Reality\n- {placeholder_token}\n",
        encoding="utf-8",
    )

    scripts_dir = root_dir / "automation" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    validator_copy = scripts_dir / "validate_story_bundle.sh"
    validator_copy.write_text(VALIDATE_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    validator_copy.chmod(0o755)

    fake_runner = root_dir / "fake_runner.sh"
    runner_marker = root_dir / "runner_called.txt"
    fake_runner.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'called\\n' > "{runner_marker}"
""",
        encoding="utf-8",
    )
    fake_runner.chmod(0o755)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["AUTOMATION_RUNNER"] = str(fake_runner)

    result = run_script(["bash", str(RUN_STORY_SCRIPT), story_id], env=env)

    assert result.returncode != 0
    assert "unresolved canonical placeholder" in result.stderr
    assert not runner_marker.exists()
