#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"

AI_REVIEW_SCRIPT="$SCRIPT_DIR/ai_review_story_run.sh"
CLASSIFY_REVIEW_SCRIPT="$SCRIPT_DIR/classify_review_story_run.sh"

AI_REVIEW_FILE_NAME="ai_review_result.md"
CLASSIFICATION_FILE_NAME="review_classification.md"
GATE_RESULT_FILE_NAME="review_gate_result.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_gate_dirty_working_tree() {
  local story_id="$1"
  {
    printf "ERROR: review gate blocked for '%s'\n" "$story_id"
    printf 'Reason: current branch has uncommitted changes; review artifacts would not match committed state\n'
    printf 'Required action:\n'
    printf ' - inspect and commit the materialized changes\n'
    printf ' - if needed, rerun automation/scripts/run_story.sh %s\n' "$story_id"
    printf ' - rerun automation/scripts/review_gate_story_run.sh %s\n' "$story_id"
  } >&2
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

resolve_target_run_dir() {
  local story_runs_root="$1"
  local run_dir_override="$2"

  if [[ -n "$run_dir_override" ]]; then
    [[ -d "$run_dir_override" ]] || fail "AUTOMATION_RUN_DIR does not exist: $run_dir_override"
    case "$run_dir_override" in
      "$story_runs_root"/*) ;;
      *) fail "AUTOMATION_RUN_DIR must be inside story run root: $story_runs_root" ;;
    esac
    printf '%s\n' "$run_dir_override"
    return 0
  fi

  resolve_latest_run_dir "$story_runs_root"
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

  local -a unique_decisions=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && unique_decisions+=("$line")
  done < <(printf '%s\n' "${decisions[@]}" | LC_ALL=C sort -u)

  decisions=("${unique_decisions[@]}")
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
  local status="$9"
  local reason="${10}"
  local tmp_file

  tmp_file="$(mktemp "${gate_result_file}.tmp.XXXXXX")"

  cat >"$tmp_file" <<EOF
{
  "story_id": "$(json_escape "$story_id")",
  "run_id": "$(json_escape "$run_id")",
  "run_dir": "$(json_escape "$run_dir")",
  "ai_review_result": "$(json_escape "$ai_review_file")",
  "review_classification_result": "$(json_escape "$classification_file")",
  "decision": "$(json_escape "$decision")",
  "status": "$(json_escape "$status")",
  "decision_source": "$(json_escape "$decision_source")",
  "reason": "$(json_escape "$reason")"
}
EOF
  mv "$tmp_file" "$gate_result_file"
}


append_manifest_artifact() {
  local manifest_file="$1"
  local artifact_name="$2"

  grep -Fqx -- "- $artifact_name" "$manifest_file" && return 0
  printf '%s\n' "- $artifact_name" >>"$manifest_file"
}

update_manifest_gate_artifacts() {
  local manifest_file="$1"
  local run_dir="$2"

  [[ -f "$manifest_file" ]] || return 0
  grep -Fq "## Artifacts" "$manifest_file" || return 0

  local artifact_name
  for artifact_name in \
    "ai_review_result.md" \
    "review_classification.md" \
    "review_gate_result.json"
  do
    [[ -f "$run_dir/$artifact_name" ]] || continue
    append_manifest_artifact "$manifest_file" "$artifact_name"
  done
}

[[ $# -eq 1 ]] || usage

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"
RUN_ID="$(basename "$LATEST_RUN_DIR")"
AI_REVIEW_FILE="$LATEST_RUN_DIR/$AI_REVIEW_FILE_NAME"
CLASSIFICATION_FILE="$LATEST_RUN_DIR/$CLASSIFICATION_FILE_NAME"
GATE_RESULT_FILE="$LATEST_RUN_DIR/$GATE_RESULT_FILE_NAME"
MANIFEST_FILE="$LATEST_RUN_DIR/manifest.md"

if working_tree_dirty; then
  fail_review_gate_dirty_working_tree "$STORY_ID"
fi

set +e
AUTOMATION_RUN_DIR="$LATEST_RUN_DIR" "$AI_REVIEW_SCRIPT" "$STORY_ID"
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
    "ai_review_failed" \
    "failed" \
    "AI review step failed"
  update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
  fail "AI review step failed for '$STORY_ID' (exit $ai_review_exit_code)"
fi

require_file "$AI_REVIEW_FILE"

decision="reject"
status="failed"
decision_source="invalid_or_missing_merge_recommendation"
reason="Classification output did not contain a valid merge recommendation"

set +e
AUTOMATION_RUN_DIR="$LATEST_RUN_DIR" "$CLASSIFY_REVIEW_SCRIPT" "$STORY_ID"
classification_exit_code=$?
set -e

if [[ $classification_exit_code -eq 0 ]]; then
  if [[ -f "$CLASSIFICATION_FILE" ]]; then
    if merge_recommendation="$(extract_merge_recommendation "$CLASSIFICATION_FILE")"; then
      decision="$merge_recommendation"
      if [[ "$decision" == "approve" ]]; then
        status="passed"
        reason="Review classification approved merge"
      else
        reason="Review classification rejected merge"
      fi
      decision_source="review_classification"
    else
      decision_source="invalid_or_missing_merge_recommendation"
      reason="Review classification artifact did not contain a valid merge recommendation"
    fi
  else
    decision_source="review_classification_missing_artifact"
    reason="Review classification step exited successfully but did not write review_classification.md"
  fi
else
  if [[ -f "$CLASSIFICATION_FILE" ]]; then
    decision_source="invalid_or_missing_merge_recommendation"
    reason="Review classification artifact did not contain a valid merge recommendation"
  else
    decision_source="review_classification_failed"
    reason="Review classification step failed"
  fi
fi

write_gate_result \
  "$GATE_RESULT_FILE" \
  "$STORY_ID" \
  "$RUN_ID" \
  "$LATEST_RUN_DIR" \
  "$AI_REVIEW_FILE" \
  "$CLASSIFICATION_FILE" \
  "$decision" \
  "$decision_source" \
  "$status" \
  "$reason"

update_manifest_gate_artifacts "$MANIFEST_FILE" "$LATEST_RUN_DIR"
printf 'Review gate result written: %s\n' "$GATE_RESULT_FILE"
printf 'Final decision: %s\n' "$decision"

if [[ $classification_exit_code -ne 0 ]]; then
  fail "review classification step failed for '$STORY_ID' (exit $classification_exit_code); gate rejected"
fi

if [[ "$decision" != "approve" ]]; then
  fail "review gate rejected merge for '$STORY_ID' (decision: $decision, source: $decision_source)"
fi
