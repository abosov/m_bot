#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
GIT_BIN="${FINALIZE_STORY_GIT_BIN:-git}"
GH_BIN="${FINALIZE_STORY_GH_BIN:-gh}"
MAIN_BRANCH="${FINALIZE_STORY_MAIN_BRANCH:-main}"
# shellcheck source=automation/scripts/story_change_ledger.sh
source "$SCRIPT_DIR/story_change_ledger.sh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/finalize_story.sh [PR_NUMBER]

Examples:
  automation/scripts/finalize_story.sh
  automation/scripts/finalize_story.sh 123
EOF
  exit 1
}

restore_ephemeral_story_change_ledger() {
  git -C "$ROOT_DIR" restore --worktree --source=HEAD -- automation/story_change_ledger.jsonl >/dev/null 2>&1 || true
}

require_clean_tree() {
  local status_output
  if ! status_output="$("$GIT_BIN" status --porcelain -- . ':(exclude)automation/story_change_ledger.jsonl')"; then
    fail "failed to inspect git working tree"
  fi

  [[ -z "$status_output" ]] || fail "working tree must be clean before finalization"
}

current_branch() {
  local branch_name
  if ! branch_name="$("$GIT_BIN" rev-parse --abbrev-ref HEAD)"; then
    fail "failed to resolve current branch"
  fi

  printf '%s\n' "$branch_name"
}

resolve_pr_number() {
  local selector="${1:-}"
  local pr_number

  if ! pr_number="$("$GH_BIN" pr view "$selector" --json number --jq '.number')"; then
    fail "could not resolve a pull request for '$selector'"
  fi

  [[ -n "$pr_number" ]] || fail "pull request number resolved empty for '$selector'"
  printf '%s\n' "$pr_number"
}

resolve_pr_head_ref() {
  local pr_number="$1"
  local head_ref

  if ! head_ref="$("$GH_BIN" pr view "$pr_number" --json headRefName --jq '.headRefName')"; then
    fail "could not resolve head branch for pull request '$pr_number'"
  fi

  [[ -n "$head_ref" ]] || fail "pull request '$pr_number' returned an empty head branch"
  printf '%s\n' "$head_ref"
}

verify_required_checks() {
  local pr_number="$1"
  local checks_output
  local exit_code=0

  set +e
  checks_output="$("$GH_BIN" pr checks "$pr_number" --required 2>&1)"
  exit_code=$?
  set -e

  if [[ $exit_code -eq 0 ]]; then
    return 0
  fi

  if echo "$checks_output" | grep -qi "no required checks reported"; then
    echo "[WARN] No required checks configured for PR '$pr_number'; falling back to all PR checks" >&2

    if ! "$GH_BIN" pr checks "$pr_number"; then
      fail "pull request '$pr_number' does not have green checks"
    fi

    return 0
  fi

  echo "$checks_output" >&2
  fail "pull request '$pr_number' does not have green required checks"
}

merge_pull_request() {
  local pr_number="$1"

  "$GH_BIN" pr merge "$pr_number" --squash --delete-branch
}

delete_local_branch_if_present() {
  local branch_name="$1"
  local local_branch

  if ! local_branch="$("$GIT_BIN" branch --list "$branch_name")"; then
    fail "failed to inspect local branch '$branch_name'"
  fi

  [[ -z "$local_branch" ]] || "$GIT_BIN" branch -D "$branch_name"
}

delete_remote_branch_if_present() {
  local branch_name="$1"

  if "$GIT_BIN" ls-remote --exit-code --heads origin "$branch_name" >/dev/null 2>&1; then
    "$GIT_BIN" push origin --delete "$branch_name"
  fi
}

extract_story_id() {
  local value="${1:-}"
  local upper_value

  upper_value="$(printf '%s' "$value" | tr '[:lower:]' '[:upper:]')"
  if [[ "$upper_value" =~ (US-[A-Z0-9]+(-[A-Z0-9]+)*) ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi

  return 1
}

[[ $# -le 1 ]] || usage

PR_SELECTOR="${1:-}"

require_clean_tree

STORY_BRANCH="$(current_branch)"
[[ "$STORY_BRANCH" != "$MAIN_BRANCH" ]] || fail "refusing to finalize from '$MAIN_BRANCH'"

if [[ -n "$PR_SELECTOR" ]]; then
  PR_NUMBER="$(resolve_pr_number "$PR_SELECTOR")"
else
  PR_NUMBER="$(resolve_pr_number "$STORY_BRANCH")"
fi

PR_HEAD_REF="$(resolve_pr_head_ref "$PR_NUMBER")"
[[ "$PR_HEAD_REF" == "$STORY_BRANCH" ]] || \
  fail "pull request '$PR_NUMBER' targets branch '$PR_HEAD_REF', expected '$STORY_BRANCH'"

echo "[INFO] Finalizing branch '$STORY_BRANCH' with PR #$PR_NUMBER" >&2

verify_required_checks "$PR_NUMBER"
merge_pull_request "$PR_NUMBER"

"$GIT_BIN" checkout "$MAIN_BRANCH"
"$GIT_BIN" pull --ff-only origin "$MAIN_BRANCH"

delete_local_branch_if_present "$STORY_BRANCH"
delete_remote_branch_if_present "$STORY_BRANCH"

final_story_id="$(extract_story_id "$PR_HEAD_REF" || true)"
if [[ -n "$final_story_id" ]]; then
  append_story_change_ledger_entry \
    "$final_story_id" \
    "story_finalized" \
    "finalized" \
    "" \
    "$STORY_BRANCH" \
    "$PR_NUMBER" \
    "finalize_story" \
    "pr:$PR_NUMBER" \
    "finalize_story completed" || true
fi

restore_ephemeral_story_change_ledger

echo "[INFO] Finalization complete on '$MAIN_BRANCH'" >&2
