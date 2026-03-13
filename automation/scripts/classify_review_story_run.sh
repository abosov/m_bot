#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RULES_FILE="${CLASSIFICATION_RULES_FILE:-$ROOT_DIR/docs/90_codex/REVIEW_CLASSIFICATION_RULES.md}"
CODEX_BIN="${CODEX_BIN:-codex}"

AI_REVIEW_FILE_NAME="ai_review_result.md"
RESULT_FILE_NAME="review_classification.md"
RAW_OUTPUT_FILE_NAME="review_classification_raw_output.txt"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/classify_review_story_run.sh STORY_ID

Example:
  automation/scripts/classify_review_story_run.sh US-AUTO-6
EOF
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "required file not found: $path"
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-6)"
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

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"
require_file "$RULES_FILE"

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_latest_run_dir "$STORY_RUNS_ROOT")"
AI_REVIEW_FILE="$LATEST_RUN_DIR/$AI_REVIEW_FILE_NAME"
require_file "$AI_REVIEW_FILE"

RESULT_FILE="$LATEST_RUN_DIR/$RESULT_FILE_NAME"
RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$RAW_OUTPUT_FILE_NAME"

cmd=(
  "$CODEX_BIN"
  -a never
  exec
  -C "$ROOT_DIR"
  -s read-only
  -o "$RESULT_FILE"
)

if [[ -n "${CODEX_MODEL:-}" ]]; then
  cmd+=(-m "$CODEX_MODEL")
fi

cmd+=(-)

set +e
{
  cat <<EOF
# ${STORY_ID} REVIEW CLASSIFICATION PROMPT

## ROLE
You are the Reviewer (Architect + QA + Security) for Zumbot.

## SOURCE OF TRUTH
- $RULES_FILE

## INPUT ARTIFACTS
- AI review result: $AI_REVIEW_FILE
- Latest run directory: $LATEST_RUN_DIR

## TASK
Classify every concrete finding from the AI review result using exactly one of:
- \`MERGE BLOCKER\`
- \`MINOR IMPROVEMENT\`
- \`FOLLOW-UP STORY\`

Follow the classification rules exactly. Do not invent findings that are not supported by the AI review result.

## OUTPUT FORMAT
Return:
1. findings by classification
2. required fixes before merge
3. optional improvements
4. follow-up stories to create
5. merge recommendation (\`approve\` or \`reject\`)

## CLASSIFICATION RULES
EOF
  cat "$RULES_FILE"
  cat <<EOF

## AI REVIEW RESULT
EOF
  cat "$AI_REVIEW_FILE"
} | "${cmd[@]}" >"$RAW_OUTPUT_FILE" 2>&1
classification_exit_code=$?
set -e

if [[ $classification_exit_code -ne 0 ]]; then
  rm -f "$RESULT_FILE"
  fail "review classification command failed for '$STORY_ID' (exit $classification_exit_code). Raw output: $RAW_OUTPUT_FILE"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  rm -f "$RESULT_FILE"
  fail "review classification completed but did not write a result artifact: $RESULT_FILE"
fi

printf 'Review classification written: %s\n' "$RESULT_FILE"
