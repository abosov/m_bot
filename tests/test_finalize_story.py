from pathlib import Path
import os
import subprocess
import textwrap


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "automation" / "scripts" / "finalize_story.sh"


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def setup_repo(root_dir: Path) -> None:
    root_dir.mkdir(parents=True)
    run(["git", "init", "-b", "main"], cwd=root_dir)
    run(["git", "config", "user.email", "codex@example.com"], cwd=root_dir)
    run(["git", "config", "user.name", "Codex Test"], cwd=root_dir)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("", encoding="utf-8")

    readme = root_dir / "README.md"
    readme.write_text("base\n", encoding="utf-8")

    run(["git", "add", "."], cwd=root_dir)
    commit = run(["git", "commit", "-m", "init"], cwd=root_dir)
    assert commit.returncode == 0, commit.stderr


def write_fake_git(script_path: Path) -> None:
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "$1" == "status" && "$2" == "--porcelain" ]]; then
              status_output="${FINALIZE_TEST_GIT_STATUS_OUTPUT:-}"
              if [[ -n "$status_output" && "${FINALIZE_TEST_LEDGER_ONLY_STATUS:-0}" == "1" ]]; then
                found_exclusion="0"
                for arg in "$@"; do
                  if [[ "$arg" == ":(exclude)automation/story_change_ledger.jsonl" ]]; then
                    found_exclusion="1"
                    break
                  fi
                done
                if [[ "$found_exclusion" == "1" ]]; then
                  status_output=""
                fi
              fi
              printf '%s' "$status_output"
              exit 0
            fi

            if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" && "$3" == "HEAD" ]]; then
              printf '%s\\n' "feature/us-auto-37"
              exit 0
            fi

            if [[ "$1" == "branch" && "$2" == "--list" ]]; then
              printf '  %s\\n' "$3"
              exit 0
            fi

            if [[ "$1" == "ls-remote" && "$2" == "--exit-code" && "$3" == "--heads" ]]; then
              exit 2
            fi

            exit 0
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)


def write_fake_gh(script_path: Path) -> None:
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            if [[ "$1" == "pr" && "$2" == "view" && "$4" == "--json" && "$5" == "number" ]]; then
              printf '%s\\n' '42'
              exit 0
            fi

            if [[ "$1" == "pr" && "$2" == "view" && "$4" == "--json" && "$5" == "headRefName" ]]; then
              printf '%s\\n' 'feature/us-auto-37'
              exit 0
            fi

            exit 0
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)


def test_finalize_story_cleans_ephemeral_ledger_on_success(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_repo(root_dir)

    ledger_path = root_dir / "automation" / "story_change_ledger.jsonl"
    ledger_path.write_text('{"preexisting":true}\n', encoding="utf-8")
    run(["git", "add", str(ledger_path.relative_to(root_dir))], cwd=root_dir)
    amend = run(["git", "commit", "-m", "seed ledger content"], cwd=root_dir)
    assert amend.returncode == 0, amend.stderr

    fake_git = tmp_path / "fake_git.sh"
    fake_gh = tmp_path / "fake_gh.sh"
    write_fake_git(fake_git)
    write_fake_gh(fake_gh)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["FINALIZE_STORY_GIT_BIN"] = str(fake_git)
    env["FINALIZE_STORY_GH_BIN"] = str(fake_gh)

    result = run(["bash", str(SCRIPT_PATH)], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert "Finalization complete on 'main'" in result.stderr

    status = run(["git", "status", "--porcelain", "--", "automation/story_change_ledger.jsonl"], cwd=root_dir)
    assert status.returncode == 0, status.stderr
    assert status.stdout.strip() == ""


def test_finalize_story_allows_ledger_only_dirty_status(tmp_path: Path) -> None:
    root_dir = tmp_path / "repo"
    setup_repo(root_dir)

    fake_git = tmp_path / "fake_git.sh"
    fake_gh = tmp_path / "fake_gh.sh"
    write_fake_git(fake_git)
    write_fake_gh(fake_gh)

    env = os.environ.copy()
    env["AUTOMATION_ROOT_DIR"] = str(root_dir)
    env["FINALIZE_STORY_GIT_BIN"] = str(fake_git)
    env["FINALIZE_STORY_GH_BIN"] = str(fake_gh)
    env["FINALIZE_TEST_GIT_STATUS_OUTPUT"] = " M automation/story_change_ledger.jsonl"
    env["FINALIZE_TEST_LEDGER_ONLY_STATUS"] = "1"

    result = run(["bash", str(SCRIPT_PATH)], cwd=root_dir, env=env)

    assert result.returncode == 0, result.stderr
    assert "Finalization complete on 'main'" in result.stderr
