#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
ESCALATION_RESULT_FILE_NAME="escalation_result.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/escalate_story.sh STORY_ID <accept-as-is|force-followup|abort>

Example:
  automation/scripts/escalate_story.sh US-AUTO-28 force-followup
  AUTOMATION_RUN_DIR=automation/runs/US-AUTO-28/2026-03-24_11-00-00 automation/scripts/escalate_story.sh US-AUTO-28 accept-as-is
EOF
  exit 1
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-28)"
}

validate_action() {
  local action="$1"
  case "$action" in
    accept-as-is|force-followup|abort) ;;
    *) fail "invalid action '$action' (expected accept-as-is, force-followup, or abort)" ;;
  esac
}

normalize_path() {
  local path="$1"

  if [[ "$path" = /* ]]; then
    printf '%s\n' "$path"
  else
    printf '%s\n' "$ROOT_DIR/$path"
  fi
}

canonicalize_path() {
  local path="$1"

  python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$path"
}

manifest_value() {
  local manifest_file="$1"
  local key="$2"
  [[ -f "$manifest_file" ]] || return 0

  sed -n -E "s/^-[[:space:]]+${key}:[[:space:]]*(.*)$/\\1/p" "$manifest_file" | head -n 1
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

resolve_latest_run_dir() {
  local story_runs_root="$1"
  local latest_run_dir

  latest_run_dir="$(
    find "$story_runs_root" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort | tail -n 1
  )"

  [[ -n "$latest_run_dir" ]] || fail "no run directories found under: $story_runs_root"
  printf '%s\n' "$latest_run_dir"
}

resolve_target_run_dir() {
  local story_runs_root="$1"
  local run_dir_override="$2"
  local normalized_override canonical_override canonical_story_runs_root manifest_story_id

  if [[ -n "$run_dir_override" ]]; then
    normalized_override="$(normalize_path "$run_dir_override")"
    [[ -d "$normalized_override" ]] || fail "AUTOMATION_RUN_DIR does not exist: $normalized_override"

    canonical_override="$(canonicalize_path "$normalized_override")"
    canonical_story_runs_root="$(canonicalize_path "$story_runs_root")"

    case "$canonical_override" in
      "$canonical_story_runs_root"/*) ;;
      *) fail "AUTOMATION_RUN_DIR must be inside story run root: $story_runs_root" ;;
    esac

    manifest_story_id="$(manifest_value "$canonical_override/manifest.md" "story_id" || true)"
    if [[ -n "$manifest_story_id" && "$manifest_story_id" != "$STORY_ID" ]]; then
      fail "AUTOMATION_RUN_DIR manifest story_id '$manifest_story_id' does not match requested story '$STORY_ID'"
    fi

    printf '%s\n' "$canonical_override"
    return 0
  fi

  resolve_latest_run_dir "$story_runs_root"
}

append_manifest_artifact() {
  local manifest_file="$1"
  local artifact_name="$2"

  grep -Fqx -- "- $artifact_name" "$manifest_file" && return 0
  printf '%s\n' "- $artifact_name" >>"$manifest_file"
}

update_manifest_artifacts() {
  local manifest_file="$1"
  local run_dir="$2"

  [[ -f "$manifest_file" ]] || return 0
  grep -Fq "## Artifacts" "$manifest_file" || return 0
  [[ -f "$run_dir/$ESCALATION_RESULT_FILE_NAME" ]] || return 0
  append_manifest_artifact "$manifest_file" "$ESCALATION_RESULT_FILE_NAME"
}

write_escalation_result() {
  local escalation_result_file="$1"
  local story_id="$2"
  local run_id="$3"
  local run_dir="$4"
  local gate_result="$5"
  local decision_source="$6"
  local reason="$7"
  local previous_reject_run_id="$8"
  local action="$9"
  local resolved_at="${10}"
  local tmp_file

  tmp_file="$(mktemp "${escalation_result_file}.tmp.XXXXXX")"
  cat >"$tmp_file" <<EOF
{
  "story_id": "$(json_escape "$story_id")",
  "run_id": "$(json_escape "$run_id")",
  "run_dir": "$(json_escape "$run_dir")",
  "gate_result": "$(json_escape "$gate_result")",
  "decision_source": "$(json_escape "$decision_source")",
  "escalation_required": true,
  "status": "resolved",
  "reason": "$(json_escape "$reason")",
  "previous_reject_run_id": "$(json_escape "$previous_reject_run_id")",
  "resolution_action": "$(json_escape "$action")",
  "resolved_at": "$(json_escape "$resolved_at")"
}
EOF
  mv "$tmp_file" "$escalation_result_file"
}

resolved_timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

parse_pending_escalation_artifact() {
  local escalation_file="$1"

  python3 - "$escalation_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

required_string_fields = [
    "status",
    "decision_source",
    "gate_result",
    "reason",
    "previous_reject_run_id",
]

def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)

def reject_dupes(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            fail(f"ERROR: escalation artifact is invalid: duplicate key '{key}'")
        obj[key] = value
    return obj

try:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_dupes)
except json.JSONDecodeError as exc:
    fail(f"ERROR: escalation artifact is invalid: malformed JSON ({exc.msg})")

if not isinstance(data, dict):
    fail("ERROR: escalation artifact is invalid: expected a JSON object")

for field in required_string_fields:
    if field not in data:
        fail(f"ERROR: escalation artifact is invalid: missing required field '{field}'")
    if not isinstance(data[field], str):
        fail(f"ERROR: escalation artifact is invalid: '{field}' must be a string")

if "escalation_required" not in data:
    fail("ERROR: escalation artifact is invalid: missing required field 'escalation_required'")
if not isinstance(data["escalation_required"], bool):
    fail("ERROR: escalation artifact is invalid: 'escalation_required' must be a boolean")
if data["escalation_required"] is not True:
    fail("ERROR: escalation artifact is invalid: escalation_required is not true")

if data["status"] != "pending":
    fail("ERROR: escalation artifact is invalid: status must be pending")
if data["decision_source"] != "repeated_reject_stagnation":
    fail("ERROR: escalation artifact is invalid: decision_source must be repeated_reject_stagnation")

print(data["gate_result"])
print(data["reason"])
print(data["decision_source"])
print(data["previous_reject_run_id"])
PY
}

[[ $# -eq 2 ]] || usage

STORY_ID="$1"
ACTION="$2"

validate_story_id "$STORY_ID"
validate_action "$ACTION"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"
RUN_ID="$(basename "$RUN_DIR")"
MANIFEST_FILE="$RUN_DIR/manifest.md"
ESCALATION_RESULT_FILE="$RUN_DIR/$ESCALATION_RESULT_FILE_NAME"

[[ -f "$ESCALATION_RESULT_FILE" ]] || fail "escalation artifact not found for '$STORY_ID': $ESCALATION_RESULT_FILE"

ESCALATION_FIELDS_RAW="$(parse_pending_escalation_artifact "$ESCALATION_RESULT_FILE")"
ESCALATION_FIELDS=()
while IFS= read -r line; do
  ESCALATION_FIELDS+=("$line")
done <<< "$ESCALATION_FIELDS_RAW"

GATE_RESULT="${ESCALATION_FIELDS[0]}"
ESCALATION_REASON="${ESCALATION_FIELDS[1]}"
DECISION_SOURCE="${ESCALATION_FIELDS[2]}"
PREVIOUS_REJECT_RUN_ID="${ESCALATION_FIELDS[3]}"

write_escalation_result \
  "$ESCALATION_RESULT_FILE" \
  "$STORY_ID" \
  "$RUN_ID" \
  "$RUN_DIR" \
  "$GATE_RESULT" \
  "$DECISION_SOURCE" \
  "$ESCALATION_REASON" \
  "$PREVIOUS_REJECT_RUN_ID" \
  "$ACTION" \
  "$(resolved_timestamp)"

update_manifest_artifacts "$MANIFEST_FILE" "$RUN_DIR"

printf 'Escalation resolved for %s run %s: %s\n' "$STORY_ID" "$RUN_ID" "$ACTION"
case "$ACTION" in
  force-followup)
    printf 'Next command: automation/scripts/run_story.sh %q\n' "$STORY_ID"
    ;;
  *)
    printf 'Next command: none\n'
    ;;
esac
