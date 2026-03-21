#!/usr/bin/env bash
set -euo pipefail

LEDGER_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEDGER_ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$LEDGER_SCRIPT_DIR/../.." && pwd)}"
LEDGER_FILE_PATH="${AUTOMATION_STORY_CHANGE_LEDGER_FILE:-$LEDGER_ROOT_DIR/automation/story_change_ledger.jsonl}"

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

  LEDGER_TS="$timestamp" \
  LEDGER_STORY_ID="$story_id" \
  LEDGER_EVENT="$event" \
  LEDGER_OUTCOME="${outcome:-}" \
  LEDGER_RUN_ID="${run_id:-}" \
  LEDGER_BRANCH="${branch:-}" \
  LEDGER_PR_NUMBER="${pr_number:-}" \
  LEDGER_DECISION_SOURCE="${decision_source:-}" \
  LEDGER_ARTIFACT="${artifact:-}" \
  LEDGER_NOTE="${note:-}" \
  python3 - <<'PY' >> "$LEDGER_FILE_PATH"
import json
import os

def value(name: str):
    raw = os.environ.get(name, "")
    return raw if raw != "" else None

record = {
    "ts": os.environ["LEDGER_TS"],
    "story_id": os.environ["LEDGER_STORY_ID"],
    "event": os.environ["LEDGER_EVENT"],
    "outcome": value("LEDGER_OUTCOME"),
    "run_id": value("LEDGER_RUN_ID"),
    "branch": value("LEDGER_BRANCH"),
    "pr_number": value("LEDGER_PR_NUMBER"),
    "decision_source": value("LEDGER_DECISION_SOURCE"),
    "artifact": value("LEDGER_ARTIFACT"),
    "note": value("LEDGER_NOTE"),
}

print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
PY
}