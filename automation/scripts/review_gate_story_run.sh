#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"

AI_REVIEW_SCRIPT="$SCRIPT_DIR/ai_review_story_run.sh"
CLASSIFY_REVIEW_SCRIPT="$SCRIPT_DIR/classify_review_story_run.sh"

AI_REVIEW_FILE_NAME="ai_review_result.md"
CLASSIFICATION_FILE_NAME="review_classification.md"
GATE_RESULT_FILE_NAME="review_gate_result.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/review_gate_story_run.sh STORY_ID

Example:
  automation/scripts/review_gate_story_run.sh US-AUTO-16
EOF
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-16)"
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

extract_merge_recommendation() {
  local classification_file="$1"
  local -a decisions=()
  local line normalized

  while IFS= read -r line; do
    normalized="$(
      printf '%s\n' "$line" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/`//g; s/^[[:space:]]*[0-9]+[.)][[:space:]]*//; s/^[[:space:]]*[-*][[:space:]]*//; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]+$//'
    )"

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation[^a-z]*(approve|reject)[^a-z]*$ ]]; then
      decisions+=("${BASH_REMATCH[1]}")
    fi
  done < "$classification_file"

  if (( ${#decisions[@]} == 0 )); then
    return 1
  fi

  mapfile -t decisions < <(printf '%s\n' "${decisions[@]}" | LC_ALL=C sort -u)
  [[ ${#decisions[@]} -eq 1 ]] || return 1

  printf '%s\n' "${decisions[0]}"
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

write_gate_result() {
  local gate_result_file="$1"
  local story_id="$2"
  local run_id="$3"
  local run_dir="$4"
  local ai_review_file="$5"
  local classification_file="$6"
  local decision="$7"
  local decision_source="$8"

  cat >"$gate_result_file" <<EOF
{
  "story_id": "$(json_escape "$story_id")",
  "run_id": "$(json_escape "$run_id")",
  "run_dir": "$(json_escape "$run_dir")",
  "ai_review_result": "$(json_escape "$ai_review_file")",
  "review_classification_result": "$(json_escape "$classification_file")",
  "decision": "$(json_escape "$decision")",
  "decision_source": "$(json_escape "$decision_source")"
}
EOF
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_latest_run_dir "$STORY_RUNS_ROOT")"
RUN_ID="$(basename "$LATEST_RUN_DIR")"
AI_REVIEW_FILE="$LATEST_RUN_DIR/$AI_REVIEW_FILE_NAME"
CLASSIFICATION_FILE="$LATEST_RUN_DIR/$CLASSIFICATION_FILE_NAME"
GATE_RESULT_FILE="$LATEST_RUN_DIR/$GATE_RESULT_FILE_NAME"

set +e
"$AI_REVIEW_SCRIPT" "$STORY_ID"
ai_review_exit_code=$?
set -e
if [[ $ai_review_exit_code -ne 0 ]]; then
  write_gate_result \
    "$GATE_RESULT_FILE" \
    "$STORY_ID" \
    "$RUN_ID" \
    "$LATEST_RUN_DIR" \
    "$AI_REVIEW_FILE" \
    "$CLASSIFICATION_FILE" \
    "reject" \
    "ai_review_failed"
  fail "AI review step failed for '$STORY_ID' (exit $ai_review_exit_code)"
fi

require_file "$AI_REVIEW_FILE"

decision="reject"
decision_source="invalid_or_missing_merge_recommendation"

set +e
"$CLASSIFY_REVIEW_SCRIPT" "$STORY_ID"
classification_exit_code=$?
set -e

if [[ $classification_exit_code -eq 0 ]]; then
  require_file "$CLASSIFICATION_FILE"

  if merge_recommendation="$(extract_merge_recommendation "$CLASSIFICATION_FILE")"; then
    decision="$merge_recommendation"
    decision_source="review_classification"
  fi
else
  decision_source="review_classification_failed"
fi

write_gate_result \
  "$GATE_RESULT_FILE" \
  "$STORY_ID" \
  "$RUN_ID" \
  "$LATEST_RUN_DIR" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$decision" \
  "$decision_source"

printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
printf 'Final decision: %s\n' "$decision"

if [[ $classification_exit_code -ne 0 ]]; then
  fail "review classification step failed for '$STORY_ID' (exit $classification_exit_code); gate rejected"
fi

if [[ "$decision" != "approve" ]]; then
  fail "review gate rejected merge for '$STORY_ID' (decision: $decision, source: $decision_source)"
fi
