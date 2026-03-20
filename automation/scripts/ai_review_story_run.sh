#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${AUTOMATION_ROOT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
RUNS_ROOT="${AUTOMATION_RUNS_ROOT:-$ROOT_DIR/automation/runs}"
RUN_DIR_OVERRIDE="${AUTOMATION_RUN_DIR:-}"
CODEX_BIN="${CODEX_BIN:-codex}"

RESULT_FILE_NAME="ai_review_result.md"
RAW_OUTPUT_FILE_NAME="ai_review_raw_output.txt"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
Usage:
  automation/scripts/ai_review_story_run.sh STORY_ID

Example:
  automation/scripts/ai_review_story_run.sh US-AUTO-5
EOF
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

validate_story_id() {
  local story_id="$1"
  [[ "$story_id" =~ ^US-[A-Z0-9]+(-[A-Z0-9]+)*$ ]] || \
    fail "invalid STORY_ID '$story_id' (expected format like US-AUTO-5)"
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

[[ $# -eq 1 ]] || usage

require_cmd "$CODEX_BIN"

STORY_ID="$1"
validate_story_id "$STORY_ID"

STORY_RUNS_ROOT="$RUNS_ROOT/$STORY_ID"
[[ -d "$STORY_RUNS_ROOT" ]] || fail "story run root not found for '$STORY_ID': $STORY_RUNS_ROOT"

LATEST_RUN_DIR="$(resolve_target_run_dir "$STORY_RUNS_ROOT" "$RUN_DIR_OVERRIDE")"

required_artifacts=(
  "review_bundle.md"
  "chatgpt_review_prompt.md"
  "diff.patch"
  "changed_files.txt"
  "pytest.txt"
)

missing_artifacts=()
for artifact_name in "${required_artifacts[@]}"; do
  artifact_path="$LATEST_RUN_DIR/$artifact_name"
  if [[ ! -f "$artifact_path" ]]; then
    missing_artifacts+=("$artifact_path")
  fi
done

if (( ${#missing_artifacts[@]} > 0 )); then
  {
    echo "ERROR: latest run for '$STORY_ID' is missing required review artifacts:"
    printf ' - %s\n' "${missing_artifacts[@]}"
  } >&2
  exit 1
fi

RESULT_FILE="$LATEST_RUN_DIR/$RESULT_FILE_NAME"
RAW_OUTPUT_FILE="$LATEST_RUN_DIR/$RAW_OUTPUT_FILE_NAME"
PROMPT_FILE="$LATEST_RUN_DIR/chatgpt_review_prompt.md"

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

if [[ -n "${CODEX_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( $CODEX_EXTRA_ARGS )
  cmd+=("${extra_args[@]}")
fi

cmd+=(-)

set +e
"${cmd[@]}" < "$PROMPT_FILE" >"$RAW_OUTPUT_FILE" 2>&1
review_exit_code=$?
set -e

if [[ $review_exit_code -ne 0 ]]; then
  rm -f "$RESULT_FILE"
  fail "AI review command failed for '$STORY_ID' (exit $review_exit_code). Raw output: $RAW_OUTPUT_FILE"
fi

if [[ ! -s "$RESULT_FILE" ]]; then
  rm -f "$RESULT_FILE"
  fail "AI review completed but did not write a result artifact: $RESULT_FILE"
fi

printf 'AI review result written: %s\n' "$RESULT_FILE"
