#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/commit_story_artifacts.sh STORY_ID

Example:
  automation/scripts/commit_story_artifacts.sh US-AUTO-41
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-41)"
}

collect_dirty_paths() {
  {
    git -C "$ROOT_DIR" diff --name-only HEAD --
    git -C "$ROOT_DIR" ls-files --others --exclude-standard
  } | awk 'NF { print }' | sort -u
}

is_story_artifact_path() {
  local story_id="$1"
  local candidate="$2"

  [[ "$candidate" == "automation/bundle_packs/$story_id.bundle.md" ]] && return 0
  [[ "$candidate" == "automation/bundles/active/$story_id" ]] && return 0
  [[ "$candidate" == "automation/bundles/active/$story_id/"* ]] && return 0
  return 1
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

COMMIT_MESSAGE="chore(story): commit story artifacts for $STORY_ID before run"

eligible_paths=()
unrelated_paths=()

while IFS= read -r path; do
  [[ -n "$path" ]] || continue
  [[ "$path" == "$EPHEMERAL_LEDGER_PATH" ]] && continue

  if is_story_artifact_path "$STORY_ID" "$path"; then
    eligible_paths+=("$path")
  else
    unrelated_paths+=("$path")
  fi
done < <(collect_dirty_paths)

if (( ${#unrelated_paths[@]} > 0 )); then
  {
    echo "ERROR: commit handoff blocked by unrelated dirty paths:"
    printf ' - %s\n' "${unrelated_paths[@]}"
  } >&2
  exit 1
fi

if (( ${#eligible_paths[@]} == 0 )); then
  fail "no eligible story artifact changes found for '$STORY_ID'"
fi

git -C "$ROOT_DIR" add -- "${eligible_paths[@]}"
git -C "$ROOT_DIR" commit -m "$COMMIT_MESSAGE"
