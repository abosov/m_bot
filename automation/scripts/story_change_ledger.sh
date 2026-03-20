#!/usr/bin/env bash
set -euo pipefail

LEDGER_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEDGER_ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$LEDGER_SCRIPT_DIR/../.." && pwd)}"
LEDGER_FILE_PATH="${AUTOMATION_STORY_CHANGE_LEDGER_FILE:-$LEDGER_ROOT_DIR/automation/story_change_ledger.jsonl}"

ledger_json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

ledger_json_value_or_null() {
  local value="${1:-}"
  if [[ -n "$value" ]]; then
    printf '"%s"' "$(ledger_json_escape "$value")"
  else
    printf 'null'
  fi
}

ledger_now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

ledger_event_allowed() {
  local event="$1"
  case "$event" in
    story_started|review_outcome|story_rejected|story_finalized)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

append_story_change_ledger_entry() {
  local story_id="${1:-}"
  local event="${2:-}"
  local outcome="${3:-}"
  local run_id="${4:-}"
  local branch="${5:-}"
  local pr_number="${6:-}"
  local decision_source="${7:-}"
  local artifact="${8:-}"
  local note="${9:-}"
  local timestamp

  [[ -n "$story_id" ]] || return 1
  [[ -n "$event" ]] || return 1
  ledger_event_allowed "$event" || return 1

  timestamp="$(ledger_now_utc)"
  mkdir -p "$(dirname "$LEDGER_FILE_PATH")"
  touch "$LEDGER_FILE_PATH"

  cat >>"$LEDGER_FILE_PATH" <<EOF
{"ts":"$(ledger_json_escape "$timestamp")","story_id":"$(ledger_json_escape "$story_id")","event":"$(ledger_json_escape "$event")","outcome":$(ledger_json_value_or_null "$outcome"),"run_id":$(ledger_json_value_or_null "$run_id"),"branch":$(ledger_json_value_or_null "$branch"),"pr_number":$(ledger_json_value_or_null "$pr_number"),"decision_source":$(ledger_json_value_or_null "$decision_source"),"artifact":$(ledger_json_value_or_null "$artifact"),"note":$(ledger_json_value_or_null "$note")}
EOF
}

