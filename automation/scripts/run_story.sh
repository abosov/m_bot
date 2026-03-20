#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
BUNDLES_ROOT="${AUTOMATION_BUNDLES_ROOT:-$ROOT_DIR/automation/bundles/active}"
RUNNER="${AUTOMATION_RUNNER:-$ROOT_DIR/automation/run_codex_task.sh}"
VALIDATOR_SCRIPT="$ROOT_DIR/automation/scripts/validate_story_bundle.sh"
# shellcheck source=automation/scripts/story_change_ledger.sh
source "$SCRIPT_DIR/story_change_ledger.sh"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/run_story.sh STORY_ID

Example:
  automation/scripts/run_story.sh US-AUTO-2
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-2)"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

BUNDLE_DIR="$BUNDLES_ROOT/$STORY_ID"
MASTER_PROMPT="$BUNDLE_DIR/03_master_prompt.md"

[[ -d "$BUNDLE_DIR" ]] || fail "story bundle not found for '$STORY_ID': $BUNDLE_DIR"

required_files=(
  "00_story.md"
  "01_context_bundle.md"
  "02_file_scope.md"
  "03_master_prompt.md"
  "04_review_checklist.md"
  "05_followups.md"
  "06_manual_actions.md"
)

missing_files=()
for file_name in "${required_files[@]}"; do
  if [[ ! -f "$BUNDLE_DIR/$file_name" ]]; then
    missing_files+=("$BUNDLE_DIR/$file_name")
  fi
done

if (( ${#missing_files[@]} > 0 )); then
  {
    echo "ERROR: story bundle '$STORY_ID' is missing required files:"
    printf ' - %s\n' "${missing_files[@]}"
  } >&2
  exit 1
fi

require_file "$RUNNER"
require_file "$VALIDATOR_SCRIPT"
require_file "$MASTER_PROMPT"

echo "[INFO] Validating story bundle: $BUNDLE_DIR" >&2
"$VALIDATOR_SCRIPT" "$STORY_ID"

append_story_started_ledger_event() {
  local branch_name

  branch_name="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ "$branch_name" == "HEAD" ]]; then
    branch_name=""
  fi

  append_story_change_ledger_entry \
    "$STORY_ID" \
    "story_started" \
    "started" \
    "" \
    "$branch_name" \
    "" \
    "run_story" \
    "automation/bundles/active/$STORY_ID/03_master_prompt.md" \
    "run_story delegated to runner" || true
}

append_story_started_ledger_event

echo "[INFO] STORY_ID: $STORY_ID" >&2
echo "[INFO] Bundle dir: $BUNDLE_DIR" >&2
echo "[INFO] Master prompt: $MASTER_PROMPT" >&2
echo "[INFO] Delegating to: $RUNNER" >&2

exec "$RUNNER" "$MASTER_PROMPT"
