from pathlib import Path
import os
import subprocess
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[1]
FINALIZE_SCRIPT = REPO_ROOT / "automation" / "scripts" / "finalize_story.sh"


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


def write_fake_git(script_path: Path) -> None:
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            log_file="${FINALIZE_TEST_LOG:?}"
            printf 'git %s\\n' "$*" >> "$log_file"

            if [[ "$1" == "status" && "$2" == "--porcelain" ]]; then
              printf '%s' "${FINALIZE_TEST_GIT_STATUS_OUTPUT:-}"
              exit 0
            fi

            if [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" && "$3" == "HEAD" ]]; then
              printf '%s\\n' "${FINALIZE_TEST_GIT_BRANCH:-feature/test-story}"
              exit 0
            fi

            if [[ "$1" == "checkout" ]]; then
              exit 0
            fi

            if [[ "$1" == "pull" && "$2" == "--ff-only" && "$3" == "origin" ]]; then
              exit 0
            fi

            if [[ "$1" == "branch" && "$2" == "--list" ]]; then
              if [[ "${FINALIZE_TEST_LOCAL_BRANCH_PRESENT:-1}" == "1" ]]; then
                printf '  %s\\n' "$3"
              fi
              exit 0
            fi

            if [[ "$1" == "branch" && "$2" == "-D" ]]; then
              exit 0
            fi

            if [[ "$1" == "ls-remote" && "$2" == "--exit-code" && "$3" == "--heads" ]]; then
              if [[ "${FINALIZE_TEST_REMOTE_BRANCH_PRESENT:-1}" == "1" ]]; then
                printf 'deadbeef\\trefs/heads/%s\\n' "$5"
                exit 0
              fi
              exit 2
            fi

            if [[ "$1" == "push" && "$2" == "origin" && "$3" == "--delete" ]]; then
              exit 0
            fi

            echo "unexpected git args: $*" >&2
            exit 99
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

            log_file="${FINALIZE_TEST_LOG:?}"
            printf 'gh %s\\n' "$*" >> "$log_file"

            if [[ "$1" == "pr" && "$2" == "view" && "$4" == "--json" && "$5" == "number" ]]; then
              printf '%s\\n' "${FINALIZE_TEST_PR_NUMBER:-42}"
              exit 0
            fi

            if [[ "$1" == "pr" && "$2" == "view" && "$4" == "--json" && "$5" == "headRefName" ]]; then
              printf '%s\\n' "${FINALIZE_TEST_PR_HEAD_REF:-feature/test-story}"
              exit 0
            fi

            if [[ "$1" == "pr" && "$2" == "checks" && "$4" == "--required" ]]; then
              if [[ "${FINALIZE_TEST_CHECKS_OK:-1}" == "1" ]]; then
                exit 0
              fi
              exit 1
            fi

            if [[ "$1" == "pr" && "$2" == "merge" && "$4" == "--squash" && "$5" == "--delete-branch" ]]; then
              exit 0
            fi

            echo "unexpected gh args: $*" >&2
            exit 99
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)


def base_env(tmp_path: Path) -> dict[str, str]:
    log_file = tmp_path / "commands.log"
    git_bin = tmp_path / "fake_git.sh"
    gh_bin = tmp_path / "fake_gh.sh"
    write_fake_git(git_bin)
    write_fake_gh(gh_bin)

    env = os.environ.copy()
    env["FINALIZE_TEST_LOG"] = str(log_file)
    env["FINALIZE_STORY_GIT_BIN"] = str(git_bin)
    env["FINALIZE_STORY_GH_BIN"] = str(gh_bin)
    env["AUTOMATION_ROOT_DIR"] = str(tmp_path / "automation_root")
    env["FINALIZE_TEST_GIT_BRANCH"] = "feature/us-auto-13"
    env["FINALIZE_TEST_PR_HEAD_REF"] = "feature/us-auto-13"
    return env


def test_finalize_story_rejects_dirty_tree(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    env["FINALIZE_TEST_GIT_STATUS_OUTPUT"] = " M automation/scripts/finalize_story.sh"

    result = run_script(["bash", str(FINALIZE_SCRIPT)], env=env)

    assert result.returncode != 0
    assert "working tree must be clean" in result.stderr
    assert (tmp_path / "commands.log").read_text(encoding="utf-8").splitlines() == [
        "git status --porcelain -- . :(exclude)automation/story_change_ledger.jsonl"
    ]


def test_finalize_story_rejects_main_branch(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    env["FINALIZE_TEST_GIT_BRANCH"] = "main"

    result = run_script(["bash", str(FINALIZE_SCRIPT)], env=env)

    assert result.returncode != 0
    assert "refusing to finalize from 'main'" in result.stderr
    assert (tmp_path / "commands.log").read_text(encoding="utf-8").splitlines() == [
        "git status --porcelain -- . :(exclude)automation/story_change_ledger.jsonl",
        "git rev-parse --abbrev-ref HEAD",
    ]


def test_finalize_story_runs_expected_commands_on_success(tmp_path: Path) -> None:
    env = base_env(tmp_path)

    result = run_script(["bash", str(FINALIZE_SCRIPT)], env=env)

    assert result.returncode == 0, result.stderr
    assert "Finalization complete on 'main'" in result.stderr
    assert (tmp_path / "commands.log").read_text(encoding="utf-8").splitlines() == [
        "git status --porcelain -- . :(exclude)automation/story_change_ledger.jsonl",
        "git rev-parse --abbrev-ref HEAD",
        "gh pr view feature/us-auto-13 --json number --jq .number",
        "gh pr view 42 --json headRefName --jq .headRefName",
        "gh pr checks 42 --required",
        "gh pr merge 42 --squash --delete-branch",
        "git checkout main",
        "git pull --ff-only origin main",
        "git branch --list feature/us-auto-13",
        "git branch -D feature/us-auto-13",
        "git ls-remote --exit-code --heads origin feature/us-auto-13",
        "git push origin --delete feature/us-auto-13",
    ]
    ledger_text = (
        tmp_path / "automation_root" / "automation" / "story_change_ledger.jsonl"
    ).read_text(encoding="utf-8")
    assert '"story_id":"US-AUTO-13"' in ledger_text
    assert '"event":"story_finalized"' in ledger_text
    assert '"pr_number":"42"' in ledger_text


def test_finalize_story_blocks_merge_when_checks_fail(tmp_path: Path) -> None:
    env = base_env(tmp_path)
    env["FINALIZE_TEST_CHECKS_OK"] = "0"

    result = run_script(["bash", str(FINALIZE_SCRIPT)], env=env)

    assert result.returncode != 0
    assert "does not have green required checks" in result.stderr
    assert (tmp_path / "commands.log").read_text(encoding="utf-8").splitlines() == [
        "git status --porcelain -- . :(exclude)automation/story_change_ledger.jsonl",
        "git rev-parse --abbrev-ref HEAD",
        "gh pr view feature/us-auto-13 --json number --jq .number",
        "gh pr view 42 --json headRefName --jq .headRefName",
        "gh pr checks 42 --required",
    ]
