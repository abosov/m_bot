#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

commit_message() {
  local story_id="$1"
  echo "chore(story): commit story artifacts for $story_id before run"
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

CURRENT_BRANCH="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD)"
STORY_BRANCH_ID="$(printf '%s' "$STORY_ID" | tr '[:upper:]' '[:lower:]')"

if [[ "$CURRENT_BRANCH" == "HEAD" ]]; then
  fail "commit handoff must run on the matching story branch for '$STORY_ID', not detached HEAD"
fi

if [[ "$CURRENT_BRANCH" == "main" ]]; then
  fail "commit handoff must run on the matching story branch for '$STORY_ID', not 'main'"
fi

if [[ ! "$CURRENT_BRANCH" =~ ^(feat|fix|chore)/${STORY_BRANCH_ID}(-.*)?$ ]]; then
  fail "commit handoff must run on the matching story branch for '$STORY_ID' (for example: feat/${STORY_BRANCH_ID}-..., fix/${STORY_BRANCH_ID}-..., or chore/${STORY_BRANCH_ID}-...)"
fi

eligible_paths=()
unrelated_paths=()
STAGE_PATHS=()

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

if printf '%s\n' "${eligible_paths[@]}" | grep -Fqx "automation/bundle_packs/$STORY_ID.bundle.md"; then
  STAGE_PATHS+=("automation/bundle_packs/$STORY_ID.bundle.md")
fi

if printf '%s\n' "${eligible_paths[@]}" | grep -Eq "^automation/bundles/active/$STORY_ID(/|$)"; then
  STAGE_PATHS+=("automation/bundles/active/$STORY_ID")
fi

git -C "$ROOT_DIR" add -- "${STAGE_PATHS[@]}"
git -C "$ROOT_DIR" commit -m "$(commit_message "$STORY_ID")" -- "${STAGE_PATHS[@]}"
