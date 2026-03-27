#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
RULES_FILE="${CLASSIFICATION_RULES_FILE:-$ROOT_DIR/docs/90_codex/REVIEW_CLASSIFICATION_RULES.md}"
CODEX_BIN="${CODEX_BIN:-codex}"
EPHEMERAL_LEDGER_PATH="automation/story_change_ledger.jsonl"
EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC=":(exclude)$EPHEMERAL_LEDGER_PATH"

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

working_tree_dirty() {
  local status_output
  status_output="$(git -C "$ROOT_DIR" status --porcelain --untracked-files=normal -- . "$EPHEMERAL_LEDGER_EXCLUDE_PATHSPEC" 2>/dev/null || true)"
  [[ -n "$status_output" ]]
}

fail_review_boundary_dirty_working_tree() {
  local story_id="$1"
  local run_dir="$2"
  {
    printf "ERROR: review classification blocked for '%s'\n" "$story_id"
    printf 'Reason: workspace-only changes would make review diverge from committed HEAD and origin/main...HEAD\n'
    printf 'Required action:\n'
    printf ' - inspect the workspace-only changes\n'
    printf ' - commit the changes if they belong in the reviewed diff, or discard them if they do not\n'
    printf ' - if you committed review-relevant changes, rerun automation/scripts/run_story.sh %s\n' "$story_id"
    printf ' - inspect the pinned run with AUTOMATION_RUN_DIR=%q automation/scripts/analyze_story_run.sh %q\n' "$run_dir" "$story_id"
    printf ' - rerun AUTOMATION_RUN_DIR=%q automation/scripts/classify_review_story_run.sh %q\n' "$run_dir" "$story_id"
  } >&2
  exit 1
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

extract_merge_recommendation() {
  local classification_file="$1"
  local -a normalized_lines=()
  local -a decisions=()
  local line normalized
  local i next_line

  while IFS= read -r line || [[ -n "$line" ]]; do
    normalized="$(
      printf '%s\n' "$line" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/`//g; s/^[[:space:]]*[0-9]+[.)][[:space:]]*//; s/^[[:space:]]*[-*][[:space:]]*//; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]+$//'
    )"
    normalized_lines+=("$normalized")
  done < "$classification_file"

  for (( i=0; i<${#normalized_lines[@]}; i++ )); do
    normalized="${normalized_lines[$i]}"

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation[^a-z]*(approve|reject)[^a-z]*$ ]]; then
      decisions+=("${BASH_REMATCH[1]}")
      continue
    fi

    if [[ "$normalized" =~ ^merge[[:space:]]+recommendation[^a-z]*$ ]]; then
      if (( i + 1 < ${#normalized_lines[@]} )); then
        next_line="${normalized_lines[$((i + 1))]}"
        if [[ "$next_line" =~ ^(approve|reject)$ ]]; then
          decisions+=("${BASH_REMATCH[1]}")
        fi
      fi
    fi
  done

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
append_gate_contract() {
  local classification_file="$1"
  local merge_recommendation="$2"

  cat >>"$classification_file" <<EOF

## Review Gate Contract
MERGE RECOMMENDATION: $merge_recommendation
EOF
}

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"
require_file "$RULES_FILE"

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"

if working_tree_dirty; then
  fail_review_boundary_dirty_working_tree "$STORY_ID" "$LATEST_RUN_DIR"
fi

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

Include the final recommendation as an exact standalone line:
\`MERGE RECOMMENDATION: approve\`
or
\`MERGE RECOMMENDATION: reject\`

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

if ! merge_recommendation="$(extract_merge_recommendation "$RESULT_FILE")"; then
  fail "review classification completed but did not produce a valid merge recommendation line in: $RESULT_FILE"
fi

append_gate_contract "$RESULT_FILE" "$merge_recommendation"

printf 'Merge recommendation: %s\n' "$merge_recommendation"
printf 'Review classification written: %s\n' "$RESULT_FILE"
